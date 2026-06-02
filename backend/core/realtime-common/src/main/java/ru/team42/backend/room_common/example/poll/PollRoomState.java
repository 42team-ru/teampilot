package ru.team42.backend.room_common.example.poll;

import lombok.Data;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Data
public class PollRoomState {

    @Data
    public static class PollOption {
        private final String id;
        private final String text;
        private int votes;
    }

    private String question;
    private final List<PollOption> options = new ArrayList<>();
    /** participantId → optionId */
    private final Map<String, String> voterMap = new HashMap<>();
    private boolean open = false;

    public void addOption(String id, String text) {
        options.add(new PollOption(id, text));
    }

    public PollOption findOption(String optionId) {
        return options.stream().filter(o -> o.getId().equals(optionId)).findFirst().orElse(null);
    }

    /** @return результаты: optionId → voteCount */
    public Map<String, Integer> results() {
        Map<String, Integer> map = new HashMap<>();
        options.forEach(o -> map.put(o.getId(), o.getVotes()));
        return map;
    }
}
