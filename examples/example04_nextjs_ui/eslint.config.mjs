import { FlatCompat } from "@eslint/eslintrc";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const baseDirectory = dirname(fileURLToPath(import.meta.url));
const compat = new FlatCompat({ baseDirectory });

const configuration = [
  ...compat.extends("next/core-web-vitals"),
  { ignores: [".next/**", "node_modules/**", "coverage/**"] },
];

export default configuration;
