# room-common

Переиспользуемый фреймворк для realtime-комнат поверх Spring WebSocket + STOMP.

**Цель** — новая realtime-комната за ≤30 строк кода, без boilerplate.  
Подходит для игр, чатов, аукционов, коллаборативного редактирования, дашбордов, голосований и любых других realtime-механик.

---

## Быстрый старт

### 1. Добавить зависимость

```kotlin
// build.gradle.kts вашего модуля
implementation(project(":core:realtime-common"))
implementation(libs.spring.boot.starter.websocket)
```

### 2. Создать комнату

```java
@Component
public class ChatRoom extends RoomHandler<ChatState> {

    public ChatRoom() {
        super("chat"); // roomType → /topic/chat/{roomId} и /app/chat/{roomId}

        on("MESSAGE", MessageDto.class, this::onMessage);
        on("TYPING",  TypingDto.class,  this::onTyping);
    }

    @Override
    public ChatState initialState() { return new ChatState(); }

    private void onMessage(RoomContext ctx, MessageDto dto) {
        ctx.<ChatState>state().getMessages().add(dto);
        ctx.broadcast("NEW_MESSAGE", dto);
    }

    private void onTyping(RoomContext ctx, TypingDto dto) {
        ctx.broadcast("TYPING", Map.of("participantId", ctx.session().getParticipantId()));
    }

    @Override
    public void onConnect(RoomContext ctx) {
        // отправить историю только что подключившемуся участнику
        ctx.sendTo(ctx.session().getSessionId(), "HISTORY",
                Map.of("messages", ctx.<ChatState>state().getMessages()));
    }
}
```

Фреймворк подхватывает бин автоматически. Никаких дополнительных регистраций не нужно.

---

## Как это работает

### Жизненный цикл комнаты

```
Клиент подключается (WebSocket handshake)
  └─ RoomHandshakeInterceptor: назначает participantId, извлекает userId

Клиент подписывается на /topic/chat/room-1
  └─ RoomInstance создаётся (если ещё нет), вызывается onConnect

Клиент отправляет на /app/chat/room-1
  └─ конверт десериализуется, вызывается нужный обработчик

Клиент отключается
  └─ вызывается onDisconnect, участник удаляется,
     пустая комната уничтожается автоматически
```

### STOMP-адреса

| Направление | Адрес | Назначение |
|-------------|-------|------------|
| Клиент → Сервер | `/app/{roomType}/{roomId}` | Отправить событие |
| Сервер → Все участники | `/topic/{roomType}/{roomId}` | Broadcast в комнату |
| Сервер → Конкретный участник | `/user/queue/events` | Личное сообщение |

Клиент должен подписаться и на `/topic/...`, и на `/user/queue/events`.

### Формат сообщений

Все сообщения в обе стороны используют единый конверт:

```json
{ "event": "MESSAGE", "payload": { "text": "привет" } }
```

### Модель конкурентности

Каждый `RoomInstance` имеет **собственный однопоточный executor**.  
Все обработчики событий, lifecycle-хуки и scheduled-задачи одной комнаты выполняются строго последовательно на этом потоке.  
Это гарантирует консистентность состояния без единого `synchronized` в коде комнаты.

---

## Справочник по API

### `RoomHandler<S>`

Базовый класс для всех комнат. Объявить как Spring `@Component`.

```java
// Конструктор — задаёт roomType и регистрирует обработчики событий
protected RoomHandler(String roomType)

// Возвращает свежее состояние для каждого нового экземпляра комнаты
public abstract S initialState()

// Регистрация типизированного обработчика события
protected <T> void on(String event, Class<T> payloadType, BiConsumer<RoomContext, T> handler)

// Lifecycle-хуки (переопределять по необходимости)
public void onConnect(RoomContext ctx)     // вызывается после подписки
public void onDisconnect(RoomContext ctx)  // вызывается при отключении
public void onError(RoomContext ctx, Exception e) // необработанные исключения
```

### `RoomContext`

Контекст, доступный внутри обработчиков. Безопасен для вызова из любого хука или scheduled-задачи.

```java
RoomSession session()
// Сессия участника, который вызвал текущее событие

<S> S state()
// Мутируемое состояние комнаты. Тип выводится автоматически:
// CasinoRoomState state = ctx.state();

Map<String, RoomSession> participants()
// Все подключённые участники, ключ — sessionId

void broadcast(String event, Object payload)
// Отправить всем участникам комнаты

void sendTo(String targetSessionId, String event, Object payload)
// Личное сообщение конкретному участнику (/user/queue/events)

ScheduledFuture<?> schedule(Duration delay, Runnable task)
// Отложенный вызов. Выполняется в executor'е комнаты — мутировать state безопасно

ScheduledFuture<?> scheduleAtFixedRate(Duration period, Runnable task)
// Периодический вызов. Тоже в executor'е комнаты

void closeRoom()
// Уничтожить комнату и остановить executor
```

### `RoomSession`

Данные одного WebSocket-соединения внутри комнаты.

```java
String sessionId      // STOMP-сессия (привязана к соединению)
String participantId  // UUID, назначается при handshake (identity участника в комнате)
Long   userId         // nullable — аутентифицированный пользователь из SecurityContext
String roomType       // например "chat"
String roomId         // например "room-1"
Map<String, Object> attributes // произвольное хранилище на сессию
```

Разница между идентификаторами:

| Идентификатор | Область | Источник |
|---------------|---------|---------|
| `sessionId` | одно WebSocket-соединение | STOMP |
| `participantId` | участник внутри комнаты | UUID при handshake |
| `userId` | глобальный пользователь | SecurityContext (nullable) |

---

## Конфигурация

```yaml
room:
  app-prefix: /app              # STOMP-префикс отправки (default: /app)
  topic-prefix: /topic          # STOMP-префикс топиков (default: /topic)
  websocket-endpoint: /ws       # путь WebSocket-эндпоинта (default: /ws)
  auto-configure-websocket: true  # false — если у вас уже есть свой WebSocket-конфиг
```

---

## Расширенные сценарии

### Кастомное извлечение userId

По умолчанию `userId` равен `null`. Переопределите бин:

```java
@Bean
public RoomHandshakeInterceptor roomHandshakeInterceptor() {
    return new RoomHandshakeInterceptor(auth -> {
        if (auth.getPrincipal() instanceof MyUserPrincipal p) return p.getId();
        return null;
    });
}
```

### Интеграция с существующим WebSocket-конфигом

Если у вас уже есть `@EnableWebSocketMessageBroker`, установите `room.auto-configure-websocket=false`  
и подключите интерцепторы вручную:

```java
@Configuration
@EnableWebSocketMessageBroker
public class MyWebSocketConfig implements WebSocketMessageBrokerConfigurer {

    @Autowired RoomHandshakeInterceptor handshakeInterceptor;
    @Autowired RoomChannelInterceptor channelInterceptor;

    @Override
    public void registerStompEndpoints(StompEndpointRegistry registry) {
        registry.addEndpoint("/ws")
                .addInterceptors(handshakeInterceptor)
                .setAllowedOriginPatterns("*")
                .withSockJS();
    }

    @Override
    public void configureMessageBroker(MessageBrokerRegistry config) {
        config.enableSimpleBroker("/topic", "/queue");
        config.setApplicationDestinationPrefixes("/app");
        config.setUserDestinationPrefix("/user");
    }

    @Override
    public void configureClientInboundChannel(ChannelRegistration registration) {
        registration.interceptors(channelInterceptor);
    }
}
```

### Таймеры и отложенные задачи

```java
private void startCountdown(RoomContext ctx) {
    // повторяется каждую секунду, выполняется в executor'е комнаты
    ScheduledFuture<?> tick = ctx.scheduleAtFixedRate(Duration.ofSeconds(1), () -> {
        MyState state = ctx.state();
        state.setCountdown(state.getCountdown() - 1);
        ctx.broadcast("TICK", Map.of("remaining", state.getCountdown()));

        if (state.getCountdown() <= 0) {
            tick.cancel(false); // отменить текущую задачу
            ctx.broadcast("START", Map.of());
        }
    });
}

// Одноразовый таймер — автозавершение игры через 60 секунд
ctx.schedule(Duration.ofSeconds(60), () -> {
    ctx.broadcast("GAME_OVER", Map.of("reason", "timeout"));
    ctx.closeRoom();
});
```

### Хранение данных в сессии

```java
public void onConnect(RoomContext ctx) {
    ctx.session().getAttributes().put("joinedAt", Instant.now());
}

private void someHandler(RoomContext ctx, SomeDto dto) {
    Instant joined = (Instant) ctx.session().getAttributes().get("joinedAt");
}
```

### Обработка ошибок

```java
@Override
public void onError(RoomContext ctx, Exception e) {
    if (e instanceof IllegalArgumentException) {
        ctx.sendTo(ctx.session().getSessionId(), "ERROR",
                Map.of("message", e.getMessage()));
    } else {
        log.error("[casino] unexpected error", e);
        ctx.sendTo(ctx.session().getSessionId(), "ERROR",
                Map.of("message", "internal error"));
    }
}
```

---

## JavaScript-клиент

```javascript
const client = new StompJs.Client({
    webSocketFactory: () => new SockJS('http://localhost:8080/ws'),
});

client.onConnect = () => {
    // подписка на broadcast комнаты
    client.subscribe('/topic/chat/room-1', frame => {
        const { event, payload } = JSON.parse(frame.body);
        console.log('room:', event, payload);
    });

    // подписка на личные сообщения
    client.subscribe('/user/queue/events', frame => {
        const { event, payload } = JSON.parse(frame.body);
        console.log('personal:', event, payload);
    });

    // отправить событие
    client.publish({
        destination: '/app/chat/room-1',
        body: JSON.stringify({ event: 'MESSAGE', payload: { text: 'привет' } })
    });
};

client.activate();
```

---

## Пример: CasinoRoom

Полный пример находится в `example/casino/CasinoRoom.java`.

Демонстрирует:
- Стейт с картой игроков и статусом игры
- Счётчик обратного отсчёта через `ctx.scheduleAtFixedRate`
- Автозавершение игры через `ctx.schedule`
- Личное приветствие при подключении через `ctx.sendTo`
- Broadcast-события: `PLAYER_JOINED`, `GAME_START`, `GAME_RESULT`

Чтобы активировать, добавьте `@Component` к классу.

Поток событий:
```
CONNECT  → WELCOME (личное)
JOIN     → PLAYER_JOINED (broadcast)
DEPOSIT  → BALANCE_UPDATED (broadcast)
READY    → PLAYER_READY (broadcast)
         → COUNTDOWN_START + COUNTDOWN_TICK × 5 (broadcast, auto)
         → GAME_START (broadcast, auto)
         → GAME_RESULT (broadcast, auto после 10 с)
```

---

## Поддерживаемые сценарии

| Сценарий | roomType | Примеры событий |
|---------|---------|----------------|
| Realtime-игры | `chess`, `poker` | `MOVE`, `SURRENDER` |
| Чат | `chat` | `MESSAGE`, `TYPING` |
| Коллаборативное редактирование | `editor` | `PATCH`, `CURSOR` |
| Аукцион | `auction` | `BID`, `LOT_CLOSED` |
| Голосование | `poll` | `VOTE`, `RESULTS` |
| Realtime-дашборд | `dashboard` | `SUBSCRIBE_METRIC` |
| Shared-сессия | `session` | `SYNC`, `ACTION` |

Фреймворк не привязан к игровой логике — бизнес-код полностью в вашем `RoomHandler`.
