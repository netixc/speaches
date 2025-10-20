import logging

from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionAudioParam,
    ChatCompletionMessageParam,
    ChatCompletionMessageToolCallParam,
    ChatCompletionStreamOptionsParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionToolParam,
    ChatCompletionUserMessageParam,
)
from openai.types.chat.chat_completion_message_tool_call_param import Function
from openai.types.chat.completion_create_params import (
    CompletionCreateParamsStreaming,
)
from openai.types.shared_params.function_definition import FunctionDefinition

from speaches.types.realtime import ConversationItem, Response

logger = logging.getLogger(__name__)


def create_completion_params(
    model_id: str, messages: list[ChatCompletionMessageParam], response: Response
) -> CompletionCreateParamsStreaming:
    assert response.output_audio_format == "pcm16"  # HACK

    max_tokens = None if response.max_response_output_tokens == "inf" else response.max_response_output_tokens
    kwargs = {}
    if len(response.tools) > 0:
        # openai.BadRequestError: Error code: 400 - {'error': {'message': "Invalid value for 'tool_choice': 'tool_choice' is only allowed when 'tools' are specified.", 'type': 'invalid_request_error', 'param': 'tool_choice', 'code': None}}
        # openai.BadRequestError: Error code: 400 - {'error': {'message': "Invalid 'tools': empty array. Expected an array with minimum length 1, but got an empty array instead.", 'type': 'invalid_request_error', 'param': 'tools', 'code': 'empty_array'}}
        # TODO: I might be able to get away with not doing any conversion here, but I'm not sure. Test it out.
        kwargs["tools"] = [
            ChatCompletionToolParam(
                type=tool.type,
                # HACK: figure out why `tool.description` is nullable
                function=FunctionDefinition(
                    name=tool.name, description=tool.description or "", parameters=tool.parameters
                ),
            )
            for tool in response.tools
        ]
        kwargs["tool_choice"] = response.tool_choice

    return CompletionCreateParamsStreaming(
        model=model_id,
        messages=[
            ChatCompletionSystemMessageParam(
                role="system",
                content=response.instructions,
            ),
            *messages,
        ],
        stream=True,
        modalities=response.modalities,
        audio=ChatCompletionAudioParam(
            voice=response.voice,  # pyright: ignore[reportArgumentType]
            format=response.output_audio_format,
        ),
        temperature=response.temperature,
        max_tokens=max_tokens,
        stream_options=ChatCompletionStreamOptionsParam(include_usage=True),
        **kwargs,
    )


def conversation_item_to_chat_message(  # noqa: PLR0911
    item: ConversationItem,
) -> ChatCompletionMessageParam | None:
    """Convert a single conversation item to a chat message.

    NOTE: function_call items are NOT handled here - they're grouped in items_to_chat_messages.
    """
    match item.type:
        case "message":
            content_list = item.content
            assert content_list is not None and len(content_list) == 1, item
            content = content_list[0]
            if item.status != "completed":
                logger.warning(f"Item {item} is not completed. Skipping.")
                return None
            match content.type:
                case "text":
                    assert content.text, content
                    return ChatCompletionAssistantMessageParam(role="assistant", content=content.text)
                case "audio":
                    assert content.transcript, content
                    return ChatCompletionAssistantMessageParam(role="assistant", content=content.transcript)
                case "input_text":
                    assert content.text, content
                    return ChatCompletionUserMessageParam(role="user", content=content.text)
                case "input_audio":
                    if not content.transcript:
                        logger.error(f"Conversation item doesn't have a non-empty transcript: {item}")
                        return None
                    return ChatCompletionUserMessageParam(role="user", content=content.transcript)
        case "function_call":
            # function_call items are handled in items_to_chat_messages to support grouping
            return None
        case "function_call_output":
            assert item.call_id and item.output, item
            return ChatCompletionToolMessageParam(
                role="tool",
                tool_call_id=item.call_id,
                content=item.output,
            )


def items_to_chat_messages(items: list[ConversationItem]) -> list[ChatCompletionMessageParam]:
    """Convert conversation items to chat messages.

    NOTE: Multiple consecutive function_call items must be grouped into a single
    assistant message with multiple tool_calls, as per OpenAI's API requirements.
    """
    messages: list[ChatCompletionMessageParam] = []
    pending_tool_calls: list[ChatCompletionMessageToolCallParam] = []

    for item in items:
        # If this is a function_call, accumulate it
        if item.type == "function_call":
            assert item.call_id and item.name and item.arguments and item.status == "completed", item
            pending_tool_calls.append(
                ChatCompletionMessageToolCallParam(
                    id=item.call_id,
                    type="function",
                    function=Function(
                        name=item.name,
                        arguments=item.arguments,
                    ),
                )
            )
            continue

        # If we hit a non-function_call item, flush any pending tool calls first
        if pending_tool_calls:
            messages.append(
                ChatCompletionAssistantMessageParam(
                    role="assistant",
                    tool_calls=pending_tool_calls.copy(),
                )
            )
            pending_tool_calls.clear()

        # Convert the current item
        chat_message = conversation_item_to_chat_message(item)
        if chat_message is not None:
            messages.append(chat_message)

    # Flush any remaining pending tool calls
    if pending_tool_calls:
        messages.append(
            ChatCompletionAssistantMessageParam(
                role="assistant",
                tool_calls=pending_tool_calls.copy(),
            )
        )

    return messages
