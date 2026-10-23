import { handle } from "@hono/aws-lambda"
import { createApp } from "./app"

export const app = createApp()
export const handler = handle(app)
