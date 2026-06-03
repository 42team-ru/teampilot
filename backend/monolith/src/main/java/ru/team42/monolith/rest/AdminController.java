package ru.team42.monolith.rest;

import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/admin")
public class AdminController {

    // Создание новой команды. Создает команду с названием, userId/telegramId/telegramUsername
    // Также возможно стоит сделать чтоб в будущем в любой запрос связанный с командой летел какой-то X-TEAM-ID
    // Помимо этой ручки не нужно ничего делать

}
