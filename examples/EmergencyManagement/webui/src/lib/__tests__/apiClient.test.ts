import { beforeEach, describe, expect, it, vi } from 'vitest';

describe('getLiveUpdatesUrl', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.unstubAllEnvs();
  });

  it('defaults to notifications stream when no override is provided', async () => {
    vi.stubEnv('VITE_API_BASE_URL', 'http://localhost:9000/gateway/');
    vi.stubEnv('VITE_UPDATES_URL', '   ');

    const { getLiveUpdatesUrl } = await import('../apiClient');

    expect(getLiveUpdatesUrl()).toBe('http://localhost:9000/gateway/notifications/stream');
  });
});
