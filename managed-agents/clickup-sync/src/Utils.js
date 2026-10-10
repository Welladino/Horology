/* String normalization and hashing. */

function norm(x) { return String(x == null ? '' : x).trim().toLowerCase(); }

function hash(x) {
  return Utilities.base64EncodeWebSafe(Utilities.computeDigest(
    Utilities.DigestAlgorithm.SHA_256, String(x))).replace(/=+$/,'');
}
