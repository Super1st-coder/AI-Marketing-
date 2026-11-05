import { randomInt } from "./random";

/**
 * Returns a random Lorem Picsum image URL.
 */
export function randomPicsumUrl(size = 256): string {
  let id = randomInt(0, 100);
  if (id === 86) {
    id = 1;
  }

  return `https://picsum.photos/id/${id}/${size}`;
}
