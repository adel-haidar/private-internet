<script setup lang="ts">
// Decorative phone frame. Slot content renders inside the phone body.
// All instances are aria-hidden — they are purely illustrative.
</script>

<template>
  <div class="pi-phone" aria-hidden="true">
    <div class="pi-phone__scr">
      <!-- status bar -->
      <div class="pi-phone__sb">
        <span>9:41</span>
        <span class="pi-phone__sb-r">
          <b />
          <b style="height: 6px" />
          <i />
        </span>
      </div>
      <!-- per-step content -->
      <div class="pi-phone__body">
        <slot />
      </div>
    </div>
  </div>
</template>
