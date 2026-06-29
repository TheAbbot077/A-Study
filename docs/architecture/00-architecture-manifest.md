# Abbot Study Architecture Manifest

## 1. Purpose

This document defines how Abbot Study must be built by humans, Copilot, Codex, and future AI agents. It establishes the architectural principles that keep the system trustworthy, extensible, and maintainable.

## 2. Core Architectural Belief

Abbot Study is not merely a study app, but an AI-native education operating system. Its architecture must support learning, assessment, analytics, administration, and intelligent automation as first-class concerns.

## 3. Foundation Before Intelligence

Deterministic architecture must exist before AI automation. The platform must have clear boundaries, stable data models, and reliable workflows before intelligence is layered on top.

## 4. Order Is Sacred

Chapter and concept order must never depend on async processing, database IDs, timestamps, queue completion order, or AI decisions. Learning structure must remain deterministic and explainable.

## 5. Views Coordinate, Services Decide, Models Persist

The backend layering rule is simple: views coordinate requests, services decide application behavior, and models persist state. This separation keeps responsibilities clear and reduces coupling.

## 6. AI Is Orchestrated, Never Scattered

No view, model, or ordinary service may call AI providers directly. All AI calls must pass through the AI Orchestrator so behavior remains controlled, observable, and replaceable.

## 7. Events Over Entanglement

Important business actions should publish Business Events so analytics, recommendations, notifications, AI, and future systems can react without tight coupling. Events enable extensibility without forcing direct dependencies.

## 8. Draft Before Official

Parser output, AI output, and generated content begin as drafts. Official learning content must be approved or compiled through trusted rules before it becomes authoritative.

## 9. Admin Control Before Automation

Powerful AI automation must be observable, reviewable, and reversible. Administrators must retain meaningful control over automated behavior.

## 10. Tests Protect the Mission

Critical invariants must be covered by automated tests. The test suite is part of the product architecture and protects correctness over time.

## 11. Codex Later, Carefully

Codex should be used only after architecture is stable and should act as an implementation assistant, not system architect. Tooling must not replace architectural judgment.

## 12. Future-Proofing Principle

Every feature should be built as if Abbot Study may later support schools, universities, professional training, oral exams, interview preparation, and lifelong learning. The architecture must remain adaptable to new educational contexts.

## 13. Final Rule

If a change makes the system more magical but less trustworthy, reject the change.
