<script setup lang="ts">
/**
 * Global share button — drop into any section.
 *
 *   <ShareButton kind="aria_track" :ref-id="track.id" :text="track.title" />
 *   <ShareButton kind="health_card" :highlight="{ headline, caption }" label="Share snapshot" />
 *
 * On click it mints a public share link, then opens the OS share sheet on mobile
 * or a platform menu (X / WhatsApp / Threads / Telegram / Facebook / Reddit /
 * Bluesky / Email + copy link) on desktop.
 */
import { ref, onBeforeUnmount } from 'vue'
import PIIcon from './PIIcon.vue'
import { useToast } from './useToast'
import {
  createShare, canNativeShare, nativeShare, shareTargets, copyLink,
  type ShareKind, type ShareHighlight, type ShareResult, type ShareTarget,
} from '../../composables/useShare'

const props = withDefaults(defineProps<{
  kind: ShareKind
  refId?: string
  highlight?: ShareHighlight
  text?: string
  label?: string
  /** 'ghost' = subtle text+icon, 'icon' = round icon-only, 'button' = filled. */
  variant?: 'ghost' | 'icon' | 'button'
}>(), { label: 'Share', variant: 'ghost' })

const toast = useToast()
const open = ref(false)
const loading = ref(false)
const targets = ref<ShareTarget[]>([])
let result: ShareResult | null = null

async function ensureShare(): Promise<ShareResult | null> {
  if (result) return result
  loading.value = true
  try {
    result = await createShare({
      kind: props.kind, refId: props.refId, highlight: props.highlight, text: props.text,
    })
    return result
  } catch {
    toast('Could not create share link', 'error')
    return null
  } finally {
    loading.value = false
  }
}

async function onTrigger() {
  if (open.value) { close(); return }
  const r = await ensureShare()
  if (!r) return
  // Mobile: try the native sheet first; fall back to our menu if cancelled.
  if (canNativeShare()) {
    const done = await nativeShare(r)
    if (done) return
  }
  targets.value = shareTargets(r)
  open.value = true
  window.addEventListener('click', onOutside, true)
  window.addEventListener('keydown', onKey)
}

function close() {
  open.value = false
  window.removeEventListener('click', onOutside, true)
  window.removeEventListener('keydown', onKey)
}

const rootEl = ref<HTMLElement | null>(null)
function onOutside(e: MouseEvent) {
  if (rootEl.value && !rootEl.value.contains(e.target as Node)) close()
}
function onKey(e: KeyboardEvent) { if (e.key === 'Escape') close() }

async function pick(t: ShareTarget) {
  if (!result) return
  if (t.copyOnly || !t.href) {
    const ok = await copyLink(result)
    toast(ok ? `Link copied — paste it in ${t.label}` : 'Copy failed', ok ? 'success' : 'error')
  } else {
    window.open(t.href, '_blank', 'noopener,noreferrer,width=600,height=560')
  }
  close()
}

async function onCopy() {
  if (!result) return
  const ok = await copyLink(result)
  toast(ok ? 'Link copied' : 'Copy failed', ok ? 'success' : 'error')
  close()
}

onBeforeUnmount(close)
</script>

<template>
  <div ref="rootEl" class="share-root">
    <button
      class="share-trigger"
      :class="`share-trigger--${variant}`"
      :disabled="loading"
      :aria-label="label"
      :title="label"
      @click.stop="onTrigger"
    >
      <PIIcon name="share" :size="variant === 'icon' ? 18 : 16" />
      <span v-if="variant !== 'icon'" class="share-trigger__label">
        {{ loading ? 'Sharing…' : label }}
      </span>
    </button>

    <div v-if="open" class="share-menu" role="menu">
      <button class="share-item share-item--copy" @click.stop="onCopy">
        <PIIcon name="link" :size="16" />
        <span>Copy link</span>
      </button>
      <div class="share-divider" />
      <button
        v-for="t in targets"
        :key="t.id"
        class="share-item"
        role="menuitem"
        @click.stop="pick(t)"
      >
        <span class="share-dot" :style="{ background: t.color }" />
        <span>{{ t.label }}</span>
        <span v-if="t.copyOnly" class="share-hint">copy</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.share-root { position: relative; display: inline-flex; }

.share-trigger {
  display: inline-flex; align-items: center; gap: 6px;
  font: inherit; font-size: 13px; font-weight: 600; cursor: pointer;
  color: var(--text-secondary); background: transparent;
  border: 1px solid transparent; border-radius: var(--radius-sm, 8px);
  padding: 6px 10px; transition: background .15s, color .15s, border-color .15s;
}
.share-trigger:hover:not(:disabled) { color: var(--text-primary); background: var(--background-elevated, rgba(255,255,255,.05)); }
.share-trigger:disabled { opacity: .6; cursor: default; }
.share-trigger--icon { padding: 7px; border-radius: 999px; }
.share-trigger--button {
  color: #fff; background: var(--accent-primary, #6b5cff);
  border-color: var(--accent-primary, #6b5cff); padding: 8px 14px;
}
.share-trigger--button:hover:not(:disabled) { filter: brightness(1.06); color: #fff; }

.share-menu {
  position: absolute; bottom: calc(100% + 8px); right: 0; z-index: 50;
  min-width: 190px; padding: 6px;
  background: var(--background-surface, #14141f);
  border: 1px solid var(--border-subtle, #26263a);
  border-radius: var(--radius-md, 12px);
  box-shadow: 0 12px 32px rgba(0, 0, 0, .45);
}
.share-item {
  display: flex; align-items: center; gap: 10px; width: 100%;
  font: inherit; font-size: 13px; text-align: left; cursor: pointer;
  color: var(--text-primary); background: transparent; border: 0;
  padding: 8px 10px; border-radius: var(--radius-sm, 8px);
}
.share-item:hover { background: var(--background-elevated, rgba(255,255,255,.06)); }
.share-item--copy { color: var(--text-primary); font-weight: 600; }
.share-divider { height: 1px; margin: 5px 6px; background: var(--border-subtle, #26263a); }
.share-dot { width: 10px; height: 10px; border-radius: 999px; flex: none; }
.share-hint {
  margin-left: auto; font-size: 10px; letter-spacing: .04em; text-transform: uppercase;
  color: var(--text-tertiary, #8a8aa0);
}
</style>
