package ru.team42.backend.room_common.example.poll;

import ru.team42.backend.room_common.context.RoomContext;
import ru.team42.backend.room_common.example.poll.dto.CreatePollDto;
import ru.team42.backend.room_common.example.poll.dto.VoteDto;
import ru.team42.backend.room_common.handler.RoomHandler;

import java.util.Map;
import java.util.UUID;

/**
 * Комната голосования в реальном времени.
 *
 * <p>Поток событий:
 * <pre>
 * CREATE_POLL  — создать опрос (организатор)
 * VOTE         — проголосовать (один голос на участника, можно переголосовать)
 * RETRACT_VOTE — отозвать голос
 * CLOSE_POLL   — завершить голосование
 * </pre>
 *
 * <p>После каждого голоса все участники получают обновлённые {@code RESULTS}.
 *
 * <p>Клиент подписывается на: {@code /topic/poll/{pollId}}
 */
// @Component
public class PollRoom extends RoomHandler<PollRoomState> {

    public PollRoom() {
        super("poll");
        on("CREATE_POLL",  CreatePollDto.class, this::createPoll);
        on("VOTE",         VoteDto.class,        this::vote);
        on("RETRACT_VOTE", VoteDto.class,        this::retractVote);
        on("CLOSE_POLL",   VoteDto.class,        this::closePoll);
    }

    @Override
    public PollRoomState initialState() {
        return new PollRoomState();
    }

    @Override
    public void onConnect(RoomContext ctx) {
        PollRoomState state = ctx.state();
        if (state.isOpen()) {
            ctx.sendTo(ctx.session().getSessionId(), "POLL_STATE", Map.of(
                    "question", state.getQuestion(),
                    "options",  state.getOptions(),
                    "results",  state.results()
            ));
        }
    }

    // -------------------------------------------------------------------------

    private void createPoll(RoomContext ctx, CreatePollDto dto) {
        PollRoomState state = ctx.state();
        if (state.isOpen()) {
            ctx.sendTo(ctx.session().getSessionId(), "ERROR",
                    Map.of("message", "Голосование уже открыто"));
            return;
        }

        state.setQuestion(dto.getQuestion());
        dto.getOptions().forEach(text -> state.addOption(UUID.randomUUID().toString(), text));
        state.setOpen(true);

        ctx.broadcast("POLL_CREATED", Map.of(
                "question", state.getQuestion(),
                "options",  state.getOptions()
        ));
    }

    private void vote(RoomContext ctx, VoteDto dto) {
        PollRoomState state = ctx.state();
        if (!state.isOpen()) {
            ctx.sendTo(ctx.session().getSessionId(), "ERROR",
                    Map.of("message", "Голосование закрыто"));
            return;
        }

        PollRoomState.PollOption option = state.findOption(dto.getOptionId());
        if (option == null) {
            ctx.sendTo(ctx.session().getSessionId(), "ERROR",
                    Map.of("message", "Неизвестный вариант: " + dto.getOptionId()));
            return;
        }

        String pid = ctx.session().getParticipantId();

        // переголосование: сначала снимаем старый голос
        String prevOptionId = state.getVoterMap().get(pid);
        if (prevOptionId != null) {
            PollRoomState.PollOption prev = state.findOption(prevOptionId);
            if (prev != null) prev.setVotes(prev.getVotes() - 1);
        }

        option.setVotes(option.getVotes() + 1);
        state.getVoterMap().put(pid, dto.getOptionId());

        ctx.broadcast("VOTE_CAST", Map.of(
                "participantId", pid,
                "optionId",      dto.getOptionId()
        ));
        ctx.broadcast("RESULTS", state.results());
    }

    private void retractVote(RoomContext ctx, VoteDto dto) {
        PollRoomState state = ctx.state();
        String pid = ctx.session().getParticipantId();
        String votedFor = state.getVoterMap().remove(pid);
        if (votedFor == null) return;

        PollRoomState.PollOption option = state.findOption(votedFor);
        if (option != null) option.setVotes(option.getVotes() - 1);

        ctx.broadcast("VOTE_RETRACTED", Map.of("participantId", pid));
        ctx.broadcast("RESULTS", state.results());
    }

    private void closePoll(RoomContext ctx, VoteDto ignored) {
        PollRoomState state = ctx.state();
        state.setOpen(false);

        // определяем победителя
        state.getOptions().stream()
                .max(java.util.Comparator.comparingInt(PollRoomState.PollOption::getVotes))
                .ifPresent(winner -> ctx.broadcast("POLL_CLOSED", Map.of(
                        "results",    state.results(),
                        "winnerId",   winner.getId(),
                        "winnerText", winner.getText(),
                        "votes",      winner.getVotes()
                )));
    }
}
