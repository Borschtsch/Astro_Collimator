"""Optional iOS root certificate profile; contains no keys or remote settings."""

import plistlib
import uuid


def certificate_profile(identity):
    identifier = "org.advancedastrocollimator.phone." + identity["ca_sha256"].replace(":", "").lower()
    description = "Optional trust for this computer's local phone video. Compare root SHA-256: " + identity["ca_sha256"]
    certificate = {"PayloadType": "com.apple.security.root", "PayloadVersion": 1,
                   "PayloadIdentifier": identifier + ".root",
                   "PayloadUUID": str(uuid.uuid5(uuid.NAMESPACE_OID, identifier + ".root")),
                   "PayloadDisplayName": "Advanced Astro Collimator local phone CA",
                   "PayloadDescription": description,
                   "PayloadCertificateFileName": "Advanced-Astro-Collimator-local-CA.cer",
                   "PayloadContent": identity["ca_der"]}
    return plistlib.dumps({"PayloadType": "Configuration", "PayloadVersion": 1,
                           "PayloadIdentifier": identifier,
                           "PayloadUUID": str(uuid.uuid5(uuid.NAMESPACE_OID, identifier)),
                           "PayloadDisplayName": "Advanced Astro Collimator phone video",
                           "PayloadDescription": description, "PayloadRemovalDisallowed": False,
                           "PayloadContent": [certificate]})
