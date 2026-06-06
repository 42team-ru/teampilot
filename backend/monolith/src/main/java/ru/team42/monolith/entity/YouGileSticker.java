package ru.team42.monolith.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.OneToMany;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import ru.team42.backend.common_data.entity.AbstractEntity;
import ru.team42.monolith.entity.enums.StickerType;

import java.util.ArrayList;
import java.util.List;

@Entity
@Table(
        name = "yougile_stickers",
        uniqueConstraints = @UniqueConstraint(
                name = "uq_yougile_stickers_team_yougile_id",
                columnNames = {"team_id", "yougile_sticker_id"}
        )
)
@Getter
@Setter
@NoArgsConstructor
public class YouGileSticker extends AbstractEntity {

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "team_id", nullable = false)
    private Team team;

    @Column(name = "yougile_sticker_id", nullable = false)
    private String yougileStickerId;

    @Column(name = "title", nullable = false)
    private String title;

    @Enumerated(EnumType.STRING)
    @Column(name = "type", nullable = false, length = 20)
    private StickerType type;

    @OneToMany(mappedBy = "sticker", fetch = FetchType.LAZY)
    private List<YouGileStickerState> states = new ArrayList<>();
}
