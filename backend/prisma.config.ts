import "dotenv/config";
import { defineConfig } from "prisma/config";

export default defineConfig({
  schema: "prisma/schema.prisma",
  migrations: { path: "prisma/migrations" },
  // Generation works without credentials; migration commands require DIRECT_URL.
  datasource: { url: process.env.DIRECT_URL ?? "" },
});
