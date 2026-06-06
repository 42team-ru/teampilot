package ru.team42.monolith.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import ru.team42.backend.common_data.entity.AbstractEntity;

@Entity
@Table(
        name = "yougile_sticker_states",
        uniqueConstraints = @UniqueConstraint(
                name = "uq_yougile_sticker_states_sticker_yougile_id",
                columnNames = {"sticker_id", "yougile_state_id"}
        )
)
@Getter
@Setter
@NoArgsConstructor
public class YouGileStickerState extends AbstractEntity {

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "sticker_id", nullable = false)
    private YouGileSticker sticker;

    @Column(name = "yougile_state_id", nullable = false)
    private String yougileStateId;

    @Column(name = "title", nullable = false)
    private String title;
}
