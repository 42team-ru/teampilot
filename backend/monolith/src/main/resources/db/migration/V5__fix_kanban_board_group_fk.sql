ALTER TABLE kanban_boards DROP COLUMN group_id;

ALTER TABLE chat_groups
    ADD COLUMN kanban_board_id UUID REFERENCES kanban_boards(id);
