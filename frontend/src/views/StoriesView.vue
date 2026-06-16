<script setup lang="ts">
import { useStories } from '../composables/useStories'
import BrainBanner from '../components/BrainBanner.vue'
import StoriesLibrary from '../components/stories/StoriesLibrary.vue'
import StoriesFilm from '../components/stories/StoriesFilm.vue'
import StoriesSeries from '../components/stories/StoriesSeries.vue'
import StoriesCategory from '../components/stories/StoriesCategory.vue'
import StoriesSearch from '../components/stories/StoriesSearch.vue'
import StoriesPlayer from '../components/stories/StoriesPlayer.vue'

const { view, watch, navigate, play, stopWatch } = useStories()
</script>

<template>
  <div class="stories-root">
    <BrainBanner />

    <!-- Sub-views -->
    <StoriesLibrary
      v-if="view.name === 'library'"
      @navigate="navigate"
      @play="play"
    />
    <StoriesFilm
      v-else-if="view.name === 'film'"
      :id="(view as any).id"
      @navigate="navigate"
      @play="play"
    />
    <StoriesSeries
      v-else-if="view.name === 'series'"
      :id="(view as any).id"
      @navigate="navigate"
      @play="play"
    />
    <StoriesCategory
      v-else-if="view.name === 'category'"
      :cat="(view as any).cat"
      @navigate="navigate"
    />
    <StoriesSearch
      v-else-if="view.name === 'search'"
      @navigate="navigate"
    />

    <!-- Fullscreen player overlay (mounts on top of everything) -->
    <StoriesPlayer
      v-if="watch"
      :item="(watch.item as any)"
      :ep="watch.ep"
      @play="play"
      @close="stopWatch"
    />
  </div>
</template>

<style scoped>
.stories-root {
  max-width: var(--content-dashboard);
  margin: 0 auto;
  padding: var(--space-8) var(--space-6);
}
</style>
