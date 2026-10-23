import { Hono } from "hono"
import { HTTPException } from "hono/http-exception"
import { z } from "zod"
import type { VideoService } from "../services/videos.js"

/** Translate HTTP input and status codes; leave business rules to the service. */
export function createVideoRoutes(service: VideoService) {
  const routes = new Hono()

  routes.post("/", async (context) => {
    let input: unknown
    try {
      input = await context.req.json()
    } catch {
      throw new HTTPException(400, {
        message: "Request body must be valid JSON",
      })
    }
    const { created, ...video } = await service.register(input)
    return context.json(video, created ? 201 : 200)
  })

  routes.get("/:videoId", async (context) => {
    const id = z.uuid().parse(context.req.param("videoId"))
    const video = await service.getById(id)
    if (!video) throw new HTTPException(404, { message: "Video not found" })
    return context.json(video)
  })

  return routes
}
