<script setup lang="ts">
import { useJobsStore } from '../../composables/useJobsStore'

const store = useJobsStore()

const hasFilters = () =>
  store.state.filterTier     !== '' ||
  store.state.filterCountry  !== '' ||
  store.state.filterStatus   !== '' ||
  store.state.filterPlatform !== ''
</script>

<template>
  <div class="filters-bar">
    <select
      :value="store.state.filterTier"
      aria-label="Filter by tier"
      @change="store.setFilter('tier', ($event.target as HTMLSelectElement).value)"
    >
      <option value="">Tier: All</option>
      <option value="STRONG_MATCH">Strong match</option>
      <option value="GOOD_MATCH">Good match</option>
      <option value="WEAK_MATCH">Weak match</option>
    </select>

    <select
      :value="store.state.filterCountry"
      aria-label="Filter by country"
      @change="store.setFilter('country', ($event.target as HTMLSelectElement).value)"
    >
      <option value="">Country: All</option>
      <option v-for="c in store.state.availableCountries" :key="c.code" :value="c.name">
        {{ c.name }}
      </option>
    </select>

    <select
      :value="store.state.filterStatus"
      aria-label="Filter by status"
      @change="store.setFilter('status', ($event.target as HTMLSelectElement).value)"
    >
      <option value="">Status: All</option>
      <option value="new">New</option>
      <option value="reviewing">Reviewing</option>
      <option value="applied">Applied</option>
      <option value="interviewing">Interviewing</option>
      <option value="rejected">Rejected</option>
      <option value="withdrawn">Withdrawn</option>
      <option value="expired">Expired</option>
    </select>

    <select
      :value="store.state.filterPlatform"
      aria-label="Filter by platform"
      @change="store.setFilter('platform', ($event.target as HTMLSelectElement).value)"
    >
      <option value="">Platform: All</option>
      <option v-for="p in store.matchPlatforms" :key="p" :value="p">{{ p }}</option>
    </select>

    <button
      v-if="hasFilters()"
      class="clear-btn"
      aria-label="Clear all filters"
      @click="store.clearFilters()"
    >
      Clear filters
    </button>
  </div>
</template>

<style scoped>
.filters-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 0;
  flex-shrink: 0;
}

select {
  background: var(--background-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm, 8px);
  color: var(--text-secondary);
  font-family: var(--font-sans);
  font-size: 13px;
  font-weight: 500;
  padding: 6px 10px;
  cursor: pointer;
  appearance: none;
  padding-right: 28px;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%239090AA' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 8px center;
  transition: border-color 0.15s, color 0.15s;
}
select:hover, select:focus {
  border-color: var(--border-medium);
  color: var(--text-primary);
  outline: none;
}

.clear-btn {
  background: none;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm, 8px);
  color: var(--text-secondary);
  font-family: var(--font-sans);
  font-size: 13px;
  font-weight: 500;
  padding: 6px 12px;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
}
.clear-btn:hover { color: var(--text-primary); border-color: var(--border-medium); }
</style>
