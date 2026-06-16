<script setup lang="ts">
/** ARIA route view (/aria). Hosts the library and the playlist detail (internal
 * view state, like StoriesView). The mini-player + Now Playing overlay live in
 * App.vue so playback persists across navigation. */
import { ref } from 'vue'
import BrainBanner from '../components/BrainBanner.vue'
import AriaLibrary from '../components/aria/AriaLibrary.vue'
import AriaPlaylist from '../components/aria/AriaPlaylist.vue'

const selected = ref<string | null>(null)
</script>

<template>
  <div class="aria-root">
    <BrainBanner />

    <AriaPlaylist
      v-if="selected"
      :playlist-id="selected"
      @back="selected = null"
    />
    <AriaLibrary v-else @open-playlist="(id) => (selected = id)" />
  </div>
</template>

<style scoped>
.aria-root {
  max-width: var(--content-dashboard);
  margin: 0 auto;
  padding: var(--space-8) var(--space-6);
}
</style>
