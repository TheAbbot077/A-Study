export type PollingOptions<T> = {
  request: (signal: AbortSignal) => Promise<T>;
  isSuccess: (value: T) => boolean;
  isFailure: (value: T) => boolean;
  intervalMs?: number;
  signal?: AbortSignal;
  onValue?: (value: T) => void;
  shouldRetryError?: (error: unknown) => boolean;
};

function wait(intervalMs: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal.aborted) {
      reject(new DOMException("Polling aborted", "AbortError"));
      return;
    }
    const timer = globalThis.setTimeout(resolve, intervalMs);
    signal.addEventListener("abort", () => {
      globalThis.clearTimeout(timer);
      reject(new DOMException("Polling aborted", "AbortError"));
    }, { once: true });
  });
}

export async function pollOperation<T>(options: PollingOptions<T>): Promise<T> {
  const controller = new AbortController();
  const abort = () => controller.abort();
  options.signal?.addEventListener("abort", abort, { once: true });
  try {
    while (true) {
      let value: T;
      try {
        value = await options.request(controller.signal);
      } catch (error) {
        if (!options.shouldRetryError?.(error)) throw error;
        await wait(options.intervalMs ?? 1500, controller.signal);
        continue;
      }
      options.onValue?.(value);
      if (options.isSuccess(value) || options.isFailure(value)) return value;
      await wait(options.intervalMs ?? 1500, controller.signal);
    }
  } finally {
    options.signal?.removeEventListener("abort", abort);
    controller.abort();
  }
}
