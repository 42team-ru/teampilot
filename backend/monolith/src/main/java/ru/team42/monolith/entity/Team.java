package ru.team42.monolith.entity;

import jakarta.persistence.CascadeType;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.OneToMany;
import jakarta.persistence.OneToOne;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import ru.team42.backend.common_data.entity.AbstractEntity;

import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "teams")
@Getter
@Setter
@NoArgsConstructor
public class Team extends AbstractEntity {

    @Column(name = "telegram_chat_id")
    private Long telegramChatId;

    @Column(name = "chat_title")
    private String chatTitle;

    @Column(name = "active", nullable = false)
    private boolean active = true;

    @Column(name = "kanban_id")
    private String kanbanId;

    @Column(name = "kanban_api_key", length = 512)
    private String kanbanApiKey;

    @OneToOne(cascade = CascadeType.ALL, orphanRemoval = true)
    @JoinColumn(name = "company_id")
    private YouGileCompany company;

    @OneToMany(mappedBy = "team", cascade = CascadeType.ALL, orphanRemoval = true, fetch = FetchType.LAZY)
    private List<TeamUser> members = new ArrayList<>();

    @OneToMany(mappedBy = "team", cascade = CascadeType.ALL, orphanRemoval = true, fetch = FetchType.LAZY)
    private List<Task> tasks = new ArrayList<>();

    @OneToMany(mappedBy = "team", cascade = CascadeType.ALL, orphanRemoval = true, fetch = FetchType.LAZY)
    private List<Meeting> meetings = new ArrayList<>();
}
