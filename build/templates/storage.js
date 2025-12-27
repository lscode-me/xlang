// Storage Keys Manager
// Централизованное управление ключами для хранения прогресса

const storageKeys = {
  // Генерация ключа для статистики теста
  // contentId: 'rutrwords' | 'rutrphrases' | 'rutrgrammar' | 'english' | 'maths' | etc.
  // level: 'a1' | 'a2' | 'b1' | 'rs5' | etc.
  quiz(contentId, level) {
    if (typeof contentId !== 'string' || typeof level !== 'string') {
      throw new Error(`Invalid parameters for quiz key: contentId=${contentId}, level=${level}`);
    }
    
    // Нормализуем входные данные в нижний регистр
    const normalizedId = contentId.toLowerCase().trim();
    const normalizedLevel = level.toLowerCase().trim();
    
    // Формат: quiz_<contentId>_<level>
    return `quiz_${normalizedId}_${normalizedLevel}`;
  },
  
  // Генерация ключа для счетчика уникальных дней
  globalDaysCounter() {
    return 'quiz_global_days-counter';
  }
};

// Storage wrapper with Telegram CloudStorage + localStorage fallback

const storage = {
  // In-memory cache to avoid repeated CloudStorage calls
  _cache: {},
  _cacheTTL: 30000, // 30 seconds
  _cloudStorageSupported: null, // Will be checked on first use

  // CloudStorage key encoding: normalize keys for CloudStorage
  // Our keys already use only safe characters (a-z, 0-9, _, -)
  _toCloudKey(key) {
    if (typeof key !== 'string') return key;
    // Keys are already normalized, just ensure length cap for safety
    const k = key.length > 128 ? key.slice(0, 128) : key;
    if (k !== key) {
      console.log(`[Storage] _toCloudKey: truncated "${key}" -> "${k}"`);
    }
    return k;
  },

  // Best-effort JSON helpers (stats are stored as JSON strings)
  _safeJsonParse(value) {
    if (!value || typeof value !== 'string') return null;
    try { return JSON.parse(value); } catch (_) { return null; }
  },

  _extractTimestamp(obj) {
    if (!obj || typeof obj !== 'object') return null;
    // Quiz stats
    if (obj.lastAttemptAt) {
      const ts = Date.parse(obj.lastAttemptAt);
      return Number.isFinite(ts) ? ts : null;
    }
    if (obj.updatedAt) {
      const ts = Date.parse(obj.updatedAt);
      return Number.isFinite(ts) ? ts : null;
    }
    // Global days counter
    if (obj.lastPassed) {
      const ts = Date.parse(String(obj.lastPassed) + 'T00:00:00Z');
      return Number.isFinite(ts) ? ts : null;
    }
    return null;
  },

  _pickNewestValue(cloudValue, localValue) {
    // Returns: { chosenValue, chosenSource, cloudValue, localValue }
    if (cloudValue && !localValue) return { chosenValue: cloudValue, chosenSource: 'cloud', cloudValue, localValue };
    if (!cloudValue && localValue) return { chosenValue: localValue, chosenSource: 'local', cloudValue, localValue };
    if (!cloudValue && !localValue) return { chosenValue: null, chosenSource: 'none', cloudValue, localValue };

    if (cloudValue === localValue) return { chosenValue: cloudValue, chosenSource: 'same', cloudValue, localValue };

    const cloudObj = this._safeJsonParse(cloudValue);
    const localObj = this._safeJsonParse(localValue);
    const cloudTs = this._extractTimestamp(cloudObj);
    const localTs = this._extractTimestamp(localObj);

    // If timestamps are available, choose newest deterministically
    if (cloudTs !== null || localTs !== null) {
      if (cloudTs === null) return { chosenValue: localValue, chosenSource: 'local', cloudValue, localValue };
      if (localTs === null) return { chosenValue: cloudValue, chosenSource: 'cloud', cloudValue, localValue };
      if (localTs > cloudTs) return { chosenValue: localValue, chosenSource: 'local', cloudValue, localValue };
      return { chosenValue: cloudValue, chosenSource: 'cloud', cloudValue, localValue };
    }

    // No timestamps: prefer CloudStorage as source of truth
    return { chosenValue: cloudValue, chosenSource: 'cloud', cloudValue, localValue };
  },

  _setCloudItem(key, value) {
    // Best-effort background sync; never throws
    try {
      if (!this.canUseCloudStorage()) return;
      const cloudKey = this._toCloudKey(key);
      window.Telegram.WebApp.CloudStorage.setItem(cloudKey, value, (error) => {
        if (error) {
          console.warn(`[Storage] Background CloudStorage SET ${key} (cloudKey=${cloudKey}) failed:`, error);
        } else {
          console.log(`[Storage] Background CloudStorage SET ${key} (cloudKey=${cloudKey}): OK`);
        }
      });
    } catch (e) {
      console.warn(`[Storage] Background CloudStorage SET ${key} exception:`, e);
    }
  },

  _capitalize(word) {
    if (!word) return word;
    return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
  },

  _canonicalizeKey(key) {
    if (typeof key !== 'string') return key;
    // Normalize to lowercase: quiz_{contentId}_{level}
    // Handle both '_' and ':' separators from legacy keys
    const parts = key.split(/[_:]/); 
    if (parts.length < 3 || parts[0] !== 'quiz') return key;
    
    // Rebuild as quiz_contentid_level (all lowercase)
    return parts.map(p => p.toLowerCase()).join('_');
  },

  _candidateKeys(key) {
    // Returns a de-duplicated list of plausible legacy keys for the same data.
    if (typeof key !== 'string') return [key];
    const canonical = this._canonicalizeKey(key);

    // Only generate variants for quiz progress keys.
    const m = canonical.match(/^quiz_([^_]+)_([^_]+)$/);
    if (!m) return [key];
    const contentId = m[1];
    const level = m[2];

    const contentIdCap = this._capitalize(contentId);
    const levelUpper = level.toUpperCase();
    const levelLower = level.toLowerCase();

    const variants = [
      key,
      canonical,
      `quiz_${contentId}_${levelUpper}`,
      `quiz_${contentIdCap}_${levelLower}`,
      `quiz_${contentIdCap}_${levelUpper}`,
      `quiz:${contentId}:${levelLower}`,
      `quiz:${contentId}:${levelUpper}`,
      `quiz:${contentIdCap}:${levelLower}`,
      `quiz:${contentIdCap}:${levelUpper}`,
    ];

    // Preserve order, remove dups
    const seen = new Set();
    const out = [];
    for (const k of variants) {
      if (typeof k !== 'string') continue;
      if (!seen.has(k)) {
        seen.add(k);
        out.push(k);
      }
    }
    return out;
  },

  _getLocalAny(keys) {
    for (const k of keys) {
      try {
        const v = localStorage.getItem(k);
        if (v !== null && v !== undefined) {
          return { key: k, value: v };
        }
      } catch (_) {}
    }
    return { key: null, value: null };
  },

  _getCloudAny(keys, timeoutMs = 5000) {
    // Tries keys sequentially until first non-empty value.
    return new Promise((resolve) => {
      if (!this.canUseCloudStorage()) {
        resolve({ key: null, value: null, error: null, timedOut: false });
        return;
      }

      let finished = false;
      const timer = setTimeout(() => {
        if (finished) return;
        finished = true;
        resolve({ key: null, value: null, error: null, timedOut: true });
      }, timeoutMs);

      const tryNext = (idx) => {
        if (finished) return;
        if (idx >= keys.length) {
          clearTimeout(timer);
          if (!finished) {
            finished = true;
            console.log(`[Storage] _getCloudAny: Tried all ${keys.length} keys, none had data`);
            resolve({ key: null, value: null, error: null, timedOut: false });
          }
          return;
        }

        const k = keys[idx];
        const cloudKey = this._toCloudKey(k);
        console.log(`[Storage] _getCloudAny: Trying key ${idx + 1}/${keys.length}: "${k}" (cloudKey: "${cloudKey}")`);
        try {
          window.Telegram.WebApp.CloudStorage.getItem(cloudKey, (error, value) => {
            if (finished) return;
            if (error) {
              // If any key errors, stop and report error.
              console.error(`[Storage] _getCloudAny: ERROR for key "${k}":`, error);
              clearTimeout(timer);
              finished = true;
              resolve({ key: k, value: null, error, timedOut: false });
              return;
            }

            if (value) {
              console.log(`[Storage] _getCloudAny: Found data for key "${k}":`, value);
              clearTimeout(timer);
              finished = true;
              resolve({ key: k, value, error: null, timedOut: false });
            } else {
              console.log(`[Storage] _getCloudAny: Key "${k}" has no data, trying next...`);
              tryNext(idx + 1);
            }
          });
        } catch (e) {
          console.error(`[Storage] _getCloudAny: EXCEPTION for key "${k}":`, e);
          clearTimeout(timer);
          finished = true;
          resolve({ key: k, value: null, error: e, timedOut: false });
        }
      };

      tryNext(0);
    });
  },
  
  // Check if CloudStorage is available
  canUseCloudStorage() {
    // Cache the result of this check
    if (this._cloudStorageSupported !== null) {
      return this._cloudStorageSupported;
    }
    
    // Check Telegram WebApp version and CloudStorage availability
    if (!window.Telegram || !window.Telegram.WebApp) {
      // Telegram WebApp object may not be available yet (script load race).
      // Do NOT permanently cache "false" here; allow later retries.
      console.log('[Storage] Telegram WebApp not available yet');
      return false;
    }
    
    // Check API version (CloudStorage requires 6.9+)
    const version = window.Telegram.WebApp.version || '0.0';
    const [major, minor] = version.split('.').map(Number);
    const versionOk = major > 6 || (major === 6 && minor >= 9);
    
    if (!versionOk) {
      console.warn(`[Storage] CloudStorage requires WebApp API 6.9+, current: ${version}`);
      this._cloudStorageSupported = false;
      return false;
    }
    
    // Check if CloudStorage object exists
    if (!window.Telegram.WebApp.CloudStorage) {
      // CloudStorage may appear after tg.ready()/script init; don't cache false permanently.
      console.warn('[Storage] CloudStorage object not available yet');
      return false;
    }
    
    // Try to check if getItem method is callable
    if (typeof window.Telegram.WebApp.CloudStorage.getItem !== 'function') {
      // Don't cache false permanently; API may not be ready yet.
      console.warn('[Storage] CloudStorage.getItem is not a function (yet)');
      return false;
    }
    
    console.log(`[Storage] CloudStorage available (API v${version})`);
    this._cloudStorageSupported = true;
    return true;
  },
  
  // Get value by key
  async get(key, options = {}) {
    return new Promise((resolve) => {
      const canonicalKey = this._canonicalizeKey(key);
      const candidates = this._candidateKeys(key);

      // Check cache first (unless forceRefresh is true)
      if (!options.forceRefresh) {
        const cached = this._cache[canonicalKey];
        if (cached && Date.now() - cached.timestamp < this._cacheTTL) {
          console.log(`[Storage] GET ${canonicalKey} from cache:`, cached.value);
          resolve(cached.value);
          return;
        }
      } else {
        console.log(`[Storage] GET ${canonicalKey} with forceRefresh - bypassing cache`);
      }

      if (!this.canUseCloudStorage()) {
        console.warn(`[Storage] GET ${canonicalKey} failed: CloudStorage not supported (cloud-only mode)`);
        resolve(null);
        return;
      }
      
      // CloudStorage is the source of truth - wait for it with generous timeout
      let resolved = false;
      let resolvedByTimeout = false;
      const timeout = setTimeout(() => {
        if (!resolved) {
          resolved = true;
          resolvedByTimeout = true;
          console.warn(`[Storage] GET ${canonicalKey} CloudStorage timeout (5s) (cloud-only mode)`);
          resolve(null);
        }
      }, 5000); // Increased timeout to 5 seconds
      
      try {
        // Probe CloudStorage across legacy keys (case variations). Canonical first.
        const cloudKeys = [canonicalKey, ...candidates.filter(k => k !== canonicalKey)];
        this._getCloudAny(cloudKeys, 5000).then((cloudHit) => {
          clearTimeout(timeout);
          const shouldResolve = !resolved;
          resolved = true;

          if (cloudHit && cloudHit.error) {
            console.error(`[Storage] CloudStorage GET ${canonicalKey} error:`, cloudHit.error);
            const msg = cloudHit.error && cloudHit.error.message ? cloudHit.error.message : '';
            if (msg && msg.includes('Unsupported')) {
              console.warn('[Storage] CloudStorage API unsupported, switching to localStorage only');
              this._cloudStorageSupported = false;
            }
            if (shouldResolve) {
              resolve(null);
            }
            return;
          }

          const cloudValue = (cloudHit && cloudHit.value) ? cloudHit.value : null;
          if (cloudHit && cloudHit.timedOut) {
            // Should not happen because we have outer timeout, but keep behavior consistent.
            if (shouldResolve) {
              resolve(null);
            }
            return;
          }

          console.log(`[Storage] GET ${canonicalKey} from CloudStorage (key=${(cloudHit && cloudHit.key) || canonicalKey}):`, cloudValue);

          // Cloud-only mode: chosen value is whatever CloudStorage has.
          const chosen = cloudValue;

          // Cache chosen value
          if (chosen !== null && chosen !== undefined) {
            this._cache[canonicalKey] = { value: chosen, timestamp: Date.now() };
          }

          // If cloud data was found under a legacy key, migrate it into canonical key for convergence.
          if (cloudValue && cloudHit && cloudHit.key && cloudHit.key !== canonicalKey) {
            console.log(`[Storage] Migrating CloudStorage legacy key → canonical for ${canonicalKey} (from ${cloudHit.key})`);
            this._setCloudItem(canonicalKey, cloudValue);
          }

          if (shouldResolve) {
            resolve(chosen || null);
          } else if (resolvedByTimeout) {
            console.log(`[Storage] CloudStorage response for ${canonicalKey} came after timeout (cloud-only mode)`);
          }
        });
      } catch (e) {
        clearTimeout(timeout);
        if (!resolved) {
          resolved = true;
          console.error(`[Storage] CloudStorage GET ${canonicalKey} exception:`, e);
          // Mark as unsupported on exception
          if (e.message && (e.message.includes('Unsupported') || e.message.includes('not supported'))) {
            console.warn('[Storage] CloudStorage API unsupported, switching to localStorage only');
            this._cloudStorageSupported = false;
          }
          resolve(null);
        }
      }
    });
  },
  
  // Set value by key
  async set(key, value) {
    return new Promise((resolve) => {
      const canonicalKey = this._canonicalizeKey(key);
      // Update cache immediately for optimistic UI
      this._cache[canonicalKey] = { value, timestamp: Date.now() };
      
      // Save to localStorage immediately for offline support
      try { localStorage.setItem(canonicalKey, value); } catch (_) {}
      console.log(`[Storage] SET ${canonicalKey} to localStorage`);
      
      if (!this.canUseCloudStorage()) {
        // Cloud-only reads are enabled, but writes still try to reach CloudStorage.
        // If Telegram is simply not ready yet, schedule a few best-effort retries.
        if (!window.Telegram || !window.Telegram.WebApp) {
          console.warn('[Storage] CloudStorage not ready yet; will retry background SET');
          const delays = [1000, 2000, 4000];
          delays.forEach((ms) => {
            setTimeout(() => {
              this._setCloudItem(canonicalKey, value);
            }, ms);
          });
          resolve({ success: true, localOnly: true, pendingCloudRetry: true });
        } else {
          console.log('[Storage] CloudStorage not supported, using localStorage only');
          resolve({ success: true, localOnly: true });
        }
        return;
      }
      
      // CloudStorage is source of truth - WAIT for it to complete
      try {
        const cloudKey = this._toCloudKey(canonicalKey);
        let finished = false;
        const timeoutMs = 3000;
        const timer = setTimeout(() => {
          if (finished) return;
          finished = true;
          console.warn(`[Storage] CloudStorage SET ${canonicalKey} (cloudKey=${cloudKey}) timed out after ${timeoutMs}ms`);
          // Best-effort background retries (non-blocking)
          this._setCloudItem(canonicalKey, value);
          resolve({ success: false, timedOut: true });
        }, timeoutMs);

        window.Telegram.WebApp.CloudStorage.setItem(cloudKey, value, (error) => {
          if (finished) return;
          finished = true;
          clearTimeout(timer);
          if (error) {
            console.error(`[Storage] CloudStorage SET ${canonicalKey} (cloudKey=${cloudKey}) FAILED:`, error);
            // Best-effort background retries (non-blocking)
            this._setCloudItem(canonicalKey, value);
            resolve({ success: false, error });
          } else {
            console.log(`[Storage] SET ${canonicalKey} to CloudStorage: OK (cloudKey=${cloudKey}) (source of truth updated)`);
            resolve({ success: true });
          }
        });
      } catch (e) {
        console.error(`[Storage] CloudStorage SET ${canonicalKey} exception:`, e);
        resolve({ success: false, error: e });
      }
    });
  },
  
  // Remove value by key
  async remove(key) {
    return new Promise((resolve) => {
      const canonicalKey = this._canonicalizeKey(key);
      // Remove from cache
      delete this._cache[canonicalKey];
      
      // Remove from localStorage
      try { localStorage.removeItem(canonicalKey); } catch (_) {}
      console.log(`[Storage] REMOVE ${canonicalKey} from localStorage`);
      
      if (!this.canUseCloudStorage()) {
        resolve();
        return;
      }
      
      // Wait for CloudStorage removal (source of truth)
      try {
        const cloudKey = this._toCloudKey(canonicalKey);
        let finished = false;
        const timeoutMs = 3000;
        const timer = setTimeout(() => {
          if (finished) return;
          finished = true;
          console.warn(`[Storage] CloudStorage REMOVE ${canonicalKey} (cloudKey=${cloudKey}) timed out after ${timeoutMs}ms`);
          resolve({ success: false, timedOut: true });
        }, timeoutMs);

        window.Telegram.WebApp.CloudStorage.removeItem(cloudKey, (error) => {
          if (finished) return;
          finished = true;
          clearTimeout(timer);
          if (error) {
            console.error(`[Storage] CloudStorage REMOVE ${canonicalKey} (cloudKey=${cloudKey}) FAILED:`, error);
            resolve({ success: false, error });
          } else {
            console.log(`[Storage] REMOVE ${canonicalKey} from CloudStorage: OK (cloudKey=${cloudKey}) (source of truth updated)`);
            resolve({ success: true });
          }
        });
      } catch (e) {
        console.error(`[Storage] CloudStorage REMOVE ${canonicalKey} exception:`, e);
        resolve({ success: false, error: e });
      }
    });
  }
};

// Export for use in other scripts
window.storageKeys = storageKeys;
window.storage = storage;
