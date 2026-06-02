1. Не делим services на impl/interface, так как это усложняет структуру проекта и не дает никакой пользы.
2. Все Kafka dto объявляем в kafka-common, куда добавляете кафку, добавляете зависимость. Топики создавать в KafkaTopics.
3. Наследуемся от AbstractEntity
4. Используем `throw new AppException(code, message)` (или статические функции, типа `AppException.unauthorized(message)`) вместо RuntimeException, чтобы было проще обрабатывать ошибки на фронте.
