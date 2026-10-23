import { Hono } from "hono";
import { HTTPException } from "hono/http-exception";
import { ZodError } from "zod";
import { createVideoRoutes } from "./http/videos.js";
import { VideoService } from "./services/videos.js";
import { VideoStorage } from "./storage/videos.js";

export function createApp(service = new VideoService(new VideoStorage())) {
  const app = new Hono();

  app.get("/", (context) => context.text("Hello Hono!"));
  app.get("/api/health", (context) => context.json({ status: "ok" }));
  app.route("/api/videos", createVideoRoutes(service));
  app.notFound((context) => context.json({ error: "NOT_FOUND" }, 404));
  app.onError((error, context) => {
    if (error instanceof ZodError) {
      return context.json(
        { error: "INVALID_REQUEST", issues: error.issues },
        422,
      );
    }
    if (error instanceof HTTPException) {
      return context.json({ error: error.message }, error.status);
    }
    console.error("Request failed", error);
    return context.json({ error: "INTERNAL_SERVER_ERROR" }, 500);
  });

  return app;
}
