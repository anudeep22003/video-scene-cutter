import * as tailwindPlugin from "prettier-plugin-tailwindcss"
import sharedConfig from "../prettier.config.mjs"

export default {
  ...sharedConfig,
  plugins: [tailwindPlugin],
  tailwindStylesheet: "src/index.css",
  tailwindFunctions: ["cn", "cva"],
}
