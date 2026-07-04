# Event Platform

## Purpose

The Event Platform provides a lightweight, in-process mechanism for domains in Abbot Study to publish business events without depending on database persistence or asynchronous infrastructure.

## What the Event Platform Owns

- the shared BusinessEvent model
- the public EventPublisher entry point
- the in-process dispatcher
- the subscriber registry
- the protocol for simple callable subscribers

## What It Does Not Own

- database event tables
- Celery tasks or worker-based delivery
- analytics-specific consumers
- notification-specific consumers
- AI event consumers
- downstream reaction policies

## Core Concepts

- Publisher: emits a BusinessEvent through EventPublisher.
- Dispatcher: invokes registered subscribers for the matching event name.
- Registry: stores subscribers by event name.
- Subscriber: a simple callable or protocol-compatible object that accepts a BusinessEvent and returns None.

## Why In-Process for Now

The initial foundation keeps event delivery synchronous and in-process so teams can experiment with event-driven design without introducing persistence, infrastructure, or operational complexity.

## Future Path

A future iteration may introduce Celery-backed delivery, durable persistence, and richer subscriber management. The core abstraction will remain compatible with that evolution.

## Domain Rule

Domains may publish business events, but they do not decide which other domains or services react to them. The Event Platform is responsible for delivery mechanics, while subscribers remain responsible for their own behavior.
