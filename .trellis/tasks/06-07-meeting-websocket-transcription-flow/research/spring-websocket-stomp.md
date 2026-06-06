# Spring WebSocket/STOMP notes

Context7 sources:

* Spring Framework current docs/Javadoc via `/websites/spring_io_spring-framework_current`.
* Spring Boot 4.0.3 docs via `/spring-projects/spring-boot/v4.0.3`.

Findings:

* Spring Framework enables broker-backed WebSocket messaging with `@EnableWebSocketMessageBroker`.
* A configuration class implements `WebSocketMessageBrokerConfigurer`.
* `registerStompEndpoints(StompEndpointRegistry registry)` registers client connection endpoints. The docs show `registry.addEndpoint("/...").withSockJS()` as a common option; plain WebSocket endpoints can be registered without SockJS fallback.
* `configureMessageBroker(MessageBrokerRegistry registry)` sets application prefixes for messages routed to annotated controllers and enables broker destinations such as `/topic` and `/queue`.
* Client messages routed to application destinations are handled by annotated message controllers with `@MessageMapping`.
* Server-side code can broadcast to subscribed destinations with Spring messaging support such as `SimpMessagingTemplate`.
* Spring Boot 4.0.3 docs identify `spring-boot-starter-websocket` as the starter that exposes Spring Framework WebSocket support for MVC applications.

Applied design:

* Add `spring-boot-starter-websocket` to the monolith.
* Use `/ws` as the STOMP endpoint.
* Use `/app` as the application destination prefix.
* Use `/topic` as the simple broker prefix.
* Route chunk sends to `/app/meetings/{meetingId}/chunks`.
* Broadcast live output to `/topic/meetings/{meetingId}/results`.
