"""Credential management service for source authentication."""

import os
import tempfile
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_token, encrypt_token
from app.models.credential import SourceCredential


class CredentialManager:
    """Manage encrypted source credentials."""

    @staticmethod
    async def store_credential(
        session: AsyncSession,
        source_id: str,
        credential_type: str,
        secret_value: str,
        created_by: Optional[int] = None,
    ) -> SourceCredential:
        """Store an encrypted credential for a source."""
        encrypted = encrypt_token(secret_value)
        cred = SourceCredential(
            id=os.urandom(8).hex(),
            source_id=source_id,
            credential_type=credential_type,
            encrypted_value=encrypted,
            created_by=created_by,
        )
        session.add(cred)
        await session.flush()
        return cred

    @staticmethod
    async def get_credential(session: AsyncSession, source_id: str) -> Optional[SourceCredential]:
        """Get the most recent credential for a source."""
        result = await session.execute(
            select(SourceCredential)
            .where(SourceCredential.source_id == source_id)
            .order_by(SourceCredential.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_all_credentials(session: AsyncSession, source_id: str) -> list[SourceCredential]:
        """Get all credentials for a source."""
        result = await session.execute(
            select(SourceCredential)
            .where(SourceCredential.source_id == source_id)
            .order_by(SourceCredential.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def delete_credential(session: AsyncSession, credential_id: str) -> bool:
        """Delete a credential by ID."""
        cred = await session.get(SourceCredential, credential_id)
        if not cred:
            return False
        await session.delete(cred)
        return True

    @staticmethod
    def decrypt_credential(cred: SourceCredential) -> str:
        """Decrypt a stored credential."""
        return decrypt_token(cred.encrypted_value)

    @staticmethod
    def get_git_auth_env(credential: SourceCredential, url: str) -> tuple[dict, Optional[str]]:
        """
        Prepare authentication for git operations.

        Returns: (env_dict, ssh_key_path)
        - env_dict: environment variables for git
        - ssh_key_path: path to temp SSH key (if applicable), must be cleaned up by caller
        """
        secret = decrypt_token(credential.encrypted_value)

        if credential.credential_type == "ssh_key":
            # Write SSH key to temp file and return its path
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix="_key") as f:
                f.write(secret)
                key_path = f.name
            os.chmod(key_path, 0o600)
            return {"GIT_SSH_COMMAND": f'ssh -i "{key_path}" -o StrictHostKeyChecking=no'}, key_path

        elif credential.credential_type == "token":
            # Inject token into URL or use as bearer
            # For GitHub/GitLab, inject token before @ in URL
            if "https://" in url:
                return {}, None
            return {"GIT_TOKEN": secret}, None

        elif credential.credential_type == "basic_auth":
            # Assume format: "username:password"
            if "https://" in url:
                return {}, None
            return {}, None

        return {}, None

    @staticmethod
    def inject_token_in_url(url: str, token: str) -> str:
        """Inject token into git URL."""
        if "https://" in url:
            return url.replace("https://", f"https://{token}@")
        if "http://" in url:
            return url.replace("http://", f"http://{token}@")
        return url
