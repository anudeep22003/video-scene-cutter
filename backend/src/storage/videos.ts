import { Prisma } from "../generated/prisma/client"
import { getPrisma } from "./prisma"

export class VideoStorage {
  /** Insert metadata, recovering the existing session/file record on a unique race. */
  async createOrRecover(data: Prisma.VideoCreateInput) {
    const prisma = getPrisma()
    try {
      const video = await prisma.video.create({ data })
      return { video, created: true }
    } catch (error) {
      if (
        !(error instanceof Prisma.PrismaClientKnownRequestError) ||
        error.code !== "P2002"
      ) {
        throw error
      }
      // The unique constraint arbitrates simultaneous registrations of one file.
      const video = await prisma.video.findUnique({
        where: {
          sessionId_fileHash: {
            sessionId: data.sessionId,
            fileHash: data.fileHash,
          },
        },
      })
      if (!video) throw error
      return { video, created: false }
    }
  }

  async findById(id: string) {
    return getPrisma().video.findUnique({ where: { id } })
  }
}
