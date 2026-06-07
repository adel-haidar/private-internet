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
      <option value="STRONG_MATCH">Strong Match</option>
      <option value="GOOD_MATCH">Good Match</option>
      <option value="WEAK_MATCH">Weak Match</option>
    </select>

    <select
      :value="store.state.filterCountry"
      aria-label="Filter by country"
      @change="store.setFilter('country', ($event.target as HTMLSelectElement).value)"
    >
      <option value="">Country: All</option>
      <option value="Switzerland">Switzerland</option>
      <option value="Canada">Canada</option>
      <option value="Norway">Norway</option>
      <option value="Singapore">Singapore</option>
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
      <option value="jobs.ch">jobs.ch</option>
      <option value="linkedin">LinkedIn</option>
      <option value="indeed">Indeed</option>
      <option value="stepstone">StepStone</option>
    </select>

    <button
      v-if="hasFilters()"
      class="clear-btn"
      aria-label="Clear all filters"
      @click="store.clearFilters()"
    >
      ✕ Clear
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
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 2px;
  color: var(--text-2);
  font-family: var(--font-sans);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 6px 10px;
  cursor: pointer;
  appearance: none;
  padding-right: 24px;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%236A6B7A' stroke-width='1.5' fill='none' stroke-linecap='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 8px center;
  transition: border-color 0.12s, color 0.12s;
}
select:hover, select:focus {
  border-color: #2a2d3e;
  color: var(--text-1);
  outline: none;
}

.clear-btn {
  background: none;
  border: 1px solid var(--border);
  border-radius: 2px;
  color: var(--text-2);
  font-family: var(--font-sans);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  padding: 6px 10px;
  cursor: pointer;
  transition: color 0.12s, border-color 0.12s;
}
.clear-btn:hover { color: var(--text-1); border-color: #2a2d3e; }
</style>
