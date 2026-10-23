import { PrismaNeon } from "@prisma/adapter-neon"
import { PrismaPg } from "@prisma/adapter-pg"
import { PrismaClient } from "../generated/prisma/client.js"

let prisma: PrismaClient | undefined

/** Lazily reuse one DB client per process, including across warm Lambda requests. */
export function getPrisma(): PrismaClient {
  if (prisma) return prisma
  const connectionString = process.env.DATABASE_URL
  if (!connectionString) throw new Error("DATABASE_URL is required")
  // Default preserves existing Neon deployments; local .env selects PostgreSQL.
  const driver = process.env.DATABASE_DRIVER ?? "neon"
  if (driver !== "postgres" && driver !== "neon") {
    throw new Error("DATABASE_DRIVER must be postgres or neon")
  }
  const adapter =
    driver === "postgres"
      ? new PrismaPg({ connectionString })
      : new PrismaNeon({ connectionString })

  // Reuse one pool across requests and warm Lambda invocations.
  prisma = new PrismaClient({
    adapter,
  })
  return prisma
}
