import 'vue-router'

declare module 'vue-router' {
  interface RouteMeta {
    public?: boolean
    fullscreen?: boolean
    title?: string
  }
}
