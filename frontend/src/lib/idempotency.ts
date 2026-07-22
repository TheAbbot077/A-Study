export class OperationIdempotency {
  private readonly keys = new Map<string, string>();

  key(resourceId: string, action: string): string {
    const scope = `${resourceId}:${action}`;
    const existing = this.keys.get(scope);
    if (existing) return existing;
    const key = crypto.randomUUID();
    this.keys.set(scope, key);
    return key;
  }

  retire(resourceId: string, action: string): void {
    this.keys.delete(`${resourceId}:${action}`);
  }
}
