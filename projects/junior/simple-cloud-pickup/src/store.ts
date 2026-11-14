import { parsePickups, serializePickups, StoreError, type Pickup } from "./pickups.ts";

export async function loadPickups(bucket: R2Bucket, key: string): Promise<Pickup[]> {
  const object = await bucket.get(key);
  if (object === null) {
    return [];
  }
  let raw: string;
  try {
    raw = await object.text();
  } catch {
    throw new StoreError("Não foi possível ler as coletas armazenadas.");
  }
  return parsePickups(raw);
}

export async function savePickups(
  bucket: R2Bucket,
  key: string,
  pickups: readonly Pickup[],
): Promise<void> {
  try {
    await bucket.put(key, serializePickups(pickups), {
      httpMetadata: { contentType: "application/json; charset=utf-8" },
    });
  } catch (error) {
    if (error instanceof StoreError) {
      throw error;
    }
    throw new StoreError("Não foi possível gravar as coletas.");
  }
}
