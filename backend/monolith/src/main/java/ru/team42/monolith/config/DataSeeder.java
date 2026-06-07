package ru.team42.monolith.config;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;
import ru.team42.monolith.entity.Course;
import ru.team42.monolith.entity.User;
import ru.team42.monolith.entity.enums.CourseScope;
import ru.team42.monolith.entity.enums.SystemRole;
import ru.team42.monolith.repository.CourseRepository;
import ru.team42.monolith.repository.UserRepository;
import ru.team42.monolith.service.CourseEventPublisher;

@Slf4j
@Component
@RequiredArgsConstructor
public class DataSeeder implements ApplicationRunner {

    private final UserRepository userRepository;
    private final CourseRepository courseRepository;
    private final CourseEventPublisher courseEventPublisher;

    @Override
    public void run(ApplicationArguments args) {
        seedAdminUser(2031863132L, "eiiwoqodhkqoqo", "владмиир", "Мельник");
        seedAdminUser(713978344L, "idzey878", "Кирилл", "Пантюхин");
        seedAdminUser(1763162562L, "lagroDev", "василий", "Мельник");
        seedAdminUser(5288131710L, "VlaDoNS1", "Влад", "Лихолетов");
        seedGlobalCourses();
    }

    private void seedAdminUser(Long telegramId, String login, String firstName, String lastName) {
        User user = userRepository.findByTelegramId(telegramId)
                .orElseGet(User::new);

        user.setTelegramId(telegramId);
        user.setTelegramLogin(login);
        user.setFirstName(firstName);
        user.setLastName(lastName);
        user.setSystemRole(SystemRole.SYSTEM_ADMIN);

        userRepository.save(user);
        log.info("Seeded admin user: {}", login);
    }

    private void seedGlobalCourses() {
        seedCourse(
                "https://stepik.org/course/67/promo",
                "Python: основы и применение",
                "Базовый курс по программированию на Python: синтаксис, структуры данных, ООП и работа с файлами.",
                "Stepik"
        );
        seedCourse(
                "https://stepik.org/course/187/promo",
                "Java. Базовый курс",
                "Введение в язык Java: типы данных, классы, наследование, коллекции и исключения.",
                "Stepik"
        );
        seedCourse(
                "https://practicum.yandex.ru/web/",
                "Веб-разработчик",
                "Полный курс веб-разработки: HTML, CSS, JavaScript, React и Node.js от Яндекс Практикум.",
                "Яндекс Практикум"
        );
        seedCourse(
                "https://practicum.yandex.ru/data-analyst/",
                "Аналитик данных",
                "Курс по аналитике данных: SQL, Python, pandas, визуализация, статистика и A/B тесты.",
                "Яндекс Практикум"
        );
        seedCourse(
                "https://practicum.yandex.ru/java-developer/",
                "Java-разработчик",
                "Профессиональный курс по Java: Spring Boot, базы данных, тестирование и микросервисы.",
                "Яндекс Практикум"
        );
        seedCourse(
                "https://www.coursera.org/specializations/machine-learning-introduction",
                "Machine Learning Specialization",
                "Специализация по машинному обучению от Andrew Ng: регрессия, классификация, нейронные сети.",
                "Coursera"
        );
        seedCourse(
                "https://www.coursera.org/learn/agile-development",
                "Agile Development",
                "Курс по Agile-методологиям: Scrum, Kanban, спринты, ретроспективы и управление продуктом.",
                "Coursera"
        );
        seedCourse(
                "https://stepik.org/course/551/promo",
                "Введение в базы данных",
                "Основы реляционных баз данных, SQL-запросы, JOIN-ы, индексы и транзакции.",
                "Stepik"
        );
        seedCourse(
                "https://practicum.yandex.ru/devops/",
                "DevOps-инженер",
                "Курс по DevOps: Docker, Kubernetes, CI/CD, мониторинг и инфраструктура как код.",
                "Яндекс Практикум"
        );
        seedCourse(
                "https://stepik.org/course/58852/promo",
                "Kotlin для начинающих",
                "Изучение языка Kotlin: синтаксис, null-safety, расширения, корутины и Android-разработка.",
                "Stepik"
        );
        seedCourse(
                "https://www.youtube.com/playlist?list=PLguYmmjtxbWGwQRxXqMTQCj6FNb55aFVo",
                "Go (Golang) — полный курс",
                "Бесплатный курс по языку Go: горутины, каналы, интерфейсы и разработка API.",
                "YouTube"
        );
        seedCourse(
                "https://www.coursera.org/learn/product-management",
                "Introduction to Product Management",
                "Введение в продуктовый менеджмент: исследование рынка, дорожная карта, метрики и запуск.",
                "Coursera"
        );
        seedCourse(
                "https://practicum.yandex.ru/project-manager/",
                "Менеджер проектов",
                "Курс по управлению проектами: планирование, риски, коммуникации, Scrum и Kanban.",
                "Яндекс Практикум"
        );
        seedCourse(
                "https://stepik.org/course/94/promo",
                "Основы статистики",
                "Теория вероятностей, описательная статистика, проверка гипотез и корреляционный анализ.",
                "Stepik"
        );
        seedCourse(
                "https://www.coursera.org/learn/ui-ux-design",
                "UI/UX Design Fundamentals",
                "Основы дизайна пользовательского интерфейса: wireframing, прототипирование, Figma и юзабилити.",
                "Coursera"
        );
        seedCourse(
                "https://stepik.org/course/16278/promo",
                "JavaScript для начинающих",
                "Основы JavaScript: DOM, события, асинхронность, fetch API и работа с браузером.",
                "Stepik"
        );
        seedCourse(
                "https://practicum.yandex.ru/qa-engineer/",
                "Инженер по тестированию",
                "Курс по тестированию ПО: ручное тестирование, автоматизация, Selenium и Postman.",
                "Яндекс Практикум"
        );
        seedCourse(
                "https://www.coursera.org/learn/soft-skills-at-work",
                "Soft Skills for Career",
                "Развитие гибких навыков: коммуникация, тайм-менеджмент, лидерство и работа в команде.",
                "Coursera"
        );
    }

    private void seedCourse(String url, String title, String description, String platform) {
        if (courseRepository.existsByUrl(url)) {
            return;
        }
        Course course = new Course();
        course.setUrl(url);
        course.setTitle(title);
        course.setDescription(description + " [" + platform + "]");
        course.setScope(CourseScope.GLOBAL);
        course.setTeam(null);
        Course saved = courseRepository.save(course);
        courseEventPublisher.publishCourseIndexed(saved);
        log.info("Seeded global course: {}", title);
    }
}
