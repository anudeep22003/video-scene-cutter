import { PrismaNeon } from "@prisma/adapter-neon";
import { PrismaClient } from "../generated/prisma/client.js";

let prisma: PrismaClient | undefined;

export function getPrisma(): PrismaClient {
  if (prisma) return prisma;
  const connectionString = process.env.DATABASE_URL;
  if (!connectionString) throw new Error("DATABASE_URL is required");

  // Reuse one pool across requests and warm Lambda invocations.
  prisma = new PrismaClient({
    adapter: new PrismaNeon({ connectionString }),
  });
  return prisma;
}
