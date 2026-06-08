"""Email delivery service used by authentication flows."""

from email.message import EmailMessage
from html import escape
from html.parser import HTMLParser
import re
import smtplib
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from src.configs.configs import settings


class EmailService:
    """Service for sending transactional emails through a configurable SMTP server."""

    _ALLOWED_RICH_TEXT_TAGS = {
        "a",
        "b",
        "blockquote",
        "br",
        "div",
        "em",
        "h1",
        "h2",
        "h3",
        "hr",
        "i",
        "img",
        "li",
        "ol",
        "p",
        "strong",
        "u",
        "ul",
    }
    _VOID_RICH_TEXT_TAGS = {"br", "hr", "img"}
    _ALLOWED_RICH_TEXT_ATTRS = {
        "a": {"href"},
        "img": {"src", "alt", "width", "height"},
    }
    _DANGEROUS_CONTENT_TAGS = {"script", "style"}
    _SAFE_IMAGE_DATA_URL_PATTERN = re.compile(
        r"^data:image/(png|jpe?g|gif|webp);base64,[A-Za-z0-9+/=]+$",
        re.IGNORECASE,
    )

    class _RichTextSanitizer(HTMLParser):
        """Allow a narrow HTML subset for admin-written outreach emails."""

        def __init__(self, email_service):
            super().__init__(convert_charrefs=False)
            self._email_service = email_service
            self._result = []
            self._open_tags = []
            self._skip_depth = 0

        def handle_starttag(self, tag, attrs):
            normalized_tag = tag.lower()

            if normalized_tag in self._email_service._DANGEROUS_CONTENT_TAGS:
                self._skip_depth += 1
                return

            if self._skip_depth:
                return

            if normalized_tag not in self._email_service._ALLOWED_RICH_TEXT_TAGS:
                return

            sanitized_attrs = self._email_service._sanitize_html_attributes(
                normalized_tag, attrs
            )
            rendered_attrs = "".join(
                f' {name}="{escape(value, quote=True)}"'
                for name, value in sanitized_attrs
            )

            if normalized_tag in self._email_service._VOID_RICH_TEXT_TAGS:
                self._result.append(f"<{normalized_tag}{rendered_attrs}>")
                return

            self._result.append(f"<{normalized_tag}{rendered_attrs}>")
            self._open_tags.append(normalized_tag)

        def handle_endtag(self, tag):
            normalized_tag = tag.lower()

            if normalized_tag in self._email_service._DANGEROUS_CONTENT_TAGS:
                if self._skip_depth:
                    self._skip_depth -= 1
                return

            if self._skip_depth:
                return

            if normalized_tag not in self._email_service._ALLOWED_RICH_TEXT_TAGS:
                return

            if normalized_tag in self._email_service._VOID_RICH_TEXT_TAGS:
                return

            if normalized_tag not in self._open_tags:
                return

            while self._open_tags:
                open_tag = self._open_tags.pop()
                self._result.append(f"</{open_tag}>")
                if open_tag == normalized_tag:
                    break

        def handle_data(self, data):
            if self._skip_depth:
                return

            self._result.append(escape(data))

        def handle_entityref(self, name):
            if self._skip_depth:
                return

            self._result.append(f"&{name};")

        def handle_charref(self, name):
            if self._skip_depth:
                return

            self._result.append(f"&#{name};")

        def get_html(self):
            while self._open_tags:
                self._result.append(f"</{self._open_tags.pop()}>")

            return "".join(self._result)

    @staticmethod
    def _normalize_single_recipient(recipient) -> str:
        """Accept only one recipient per email message."""
        if isinstance(recipient, (list, tuple, set, frozenset)):
            raise RuntimeError(
                "Email delivery accepts only one recipient per message."
            )

        normalized = str(recipient or "").strip()
        if not normalized:
            raise RuntimeError("Recipient email is required.")

        if "," in normalized or ";" in normalized:
            raise RuntimeError(
                "Email delivery accepts only one recipient per message."
            )

        return normalized

    @staticmethod
    def _get_smtp_delivery_settings(require_enabled: bool = False) -> dict | None:
        """Load and validate SMTP settings used by email delivery flows."""
        smtp_enabled = EmailService._get_setting("SMTP_ENABLED", False)
        smtp_host = EmailService._normalize_smtp_value(
            EmailService._get_setting("SMTP_HOST")
        )
        smtp_port = EmailService._get_setting("SMTP_PORT", 587)
        smtp_username = EmailService._normalize_smtp_value(
            EmailService._get_setting("SMTP_USERNAME")
        )
        smtp_password = EmailService._normalize_smtp_value(
            EmailService._get_setting("SMTP_PASSWORD")
        )
        smtp_use_tls = EmailService._get_setting("SMTP_USE_TLS", True)
        smtp_use_ssl = EmailService._get_setting("SMTP_USE_SSL", False)
        smtp_from_email = EmailService._normalize_smtp_value(
            EmailService._get_setting("SMTP_FROM_EMAIL")
        )

        if not smtp_enabled:
            if require_enabled:
                raise RuntimeError(
                    "SMTP delivery is disabled. Enable SMTP_ENABLED before sending emails."
                )
            return None

        if not smtp_host or not smtp_from_email:
            raise RuntimeError(
                "SMTP is enabled but SMTP_HOST/SMTP_FROM_EMAIL are not fully configured."
            )

        if smtp_host.lower() == "smtp.gmail.com":
            if smtp_password:
                # Google app passwords are displayed in grouped blocks, but SMTP
                # authentication expects the underlying token value.
                smtp_password = smtp_password.replace(" ", "")

            if not smtp_username or not smtp_password:
                raise RuntimeError(
                    "SMTP_USERNAME/SMTP_PASSWORD must be configured when using smtp.gmail.com."
                )

        if smtp_host.lower() == "smtp.gmail.com" and (
            len(smtp_password or "") != 16
        ):
            raise RuntimeError(
                "SMTP_PASSWORD for smtp.gmail.com must be a 16-character Google app password."
            )

        return {
            "smtp_host": smtp_host,
            "smtp_port": smtp_port,
            "smtp_username": smtp_username,
            "smtp_password": smtp_password,
            "smtp_use_tls": smtp_use_tls,
            "smtp_use_ssl": smtp_use_ssl,
        }

    @staticmethod
    def _get_setting(name: str, default=None):
        """Safely read optional settings attributes with a fallback."""
        return getattr(settings, name, default)

    @staticmethod
    def _normalize_smtp_value(value: str | None) -> str | None:
        """Trim whitespace and optional wrapping quotes from SMTP settings."""
        if value is None:
            return None

        normalized = value.strip()
        if len(normalized) >= 2 and normalized[0] == normalized[-1]:
            if normalized[0] in {'"', "'"}:
                normalized = normalized[1:-1].strip()

        return normalized

    @staticmethod
    def _build_password_reset_destination(reset_token: str) -> str:
        password_reset_url = EmailService._get_setting("PASSWORD_RESET_URL")
        if password_reset_url:
            parts = urlsplit(password_reset_url)
            query_items = dict(parse_qsl(parts.query, keep_blank_values=True))
            query_items["token"] = reset_token
            updated_query = urlencode(query_items)
            return urlunsplit(
                (parts.scheme, parts.netloc, parts.path, updated_query, parts.fragment)
            )

        return reset_token

    @staticmethod
    def _build_password_reset_message(recipient: str, reset_token: str) -> EmailMessage:
        recipient = EmailService._normalize_single_recipient(recipient)
        smtp_from_email = EmailService._get_setting("SMTP_FROM_EMAIL")
        smtp_from_name = EmailService._get_setting("SMTP_FROM_NAME", "UBA Questionary")
        reset_expiration_minutes = EmailService._get_setting(
            "PASSWORD_RESET_TOKEN_EXPIRATION_MINUTES", 30
        )

        if not smtp_from_email:
            raise RuntimeError(
                "SMTP_FROM_EMAIL must be configured when SMTP is enabled."
            )

        destination = EmailService._build_password_reset_destination(reset_token)

        html_body = (
            "<html><body>"
            "<p>Ola,</p>"
            "<p>Recebemos uma solicitacao para redefinir sua senha.</p>"
            "<p>"
            f'Clique no <a href="{destination}">link de redefinicao de senha</a> '
            "para continuar."
            "</p>"
            f"<p>Este acesso expira em {reset_expiration_minutes} minutos.</p>"
            "<p>Se voce nao solicitou a redefinicao, ignore este e-mail.</p>"
            "</body></html>"
        )

        message = EmailMessage()
        message["Subject"] = "Redefinicao de senha"
        message["From"] = f"{smtp_from_name} <{smtp_from_email}>"
        message["To"] = recipient
        message.set_content(html_body, subtype="html")

        return message

    @staticmethod
    def _sanitize_html_attributes(tag: str, attrs: list[tuple[str, str | None]]) -> list[tuple[str, str]]:
        allowed_attrs = EmailService._ALLOWED_RICH_TEXT_ATTRS.get(tag, set())
        sanitized_attrs = []

        for attr_name, attr_value in attrs:
            normalized_name = (attr_name or "").lower()
            normalized_value = (attr_value or "").strip()

            if normalized_name not in allowed_attrs or not normalized_value:
                continue

            if normalized_name == "href":
                if not EmailService._is_safe_rich_text_url(
                    normalized_value,
                    allowed_schemes={"http", "https", "mailto"},
                ):
                    continue

            if normalized_name == "src":
                if not EmailService._is_safe_rich_text_url(
                    normalized_value,
                    allowed_schemes={"http", "https"},
                ):
                    continue

            if normalized_name in {"width", "height"}:
                if not normalized_value.isdigit():
                    continue

            sanitized_attrs.append((normalized_name, normalized_value))

        return sanitized_attrs

    @staticmethod
    def _is_safe_rich_text_url(url: str, allowed_schemes: set[str]) -> bool:
        parsed_url = urlsplit(url)
        scheme = (parsed_url.scheme or "").lower()

        if scheme == "data":
            return bool(EmailService._SAFE_IMAGE_DATA_URL_PATTERN.fullmatch(url))

        if scheme not in allowed_schemes:
            return False

        if scheme in {"http", "https"} and not parsed_url.netloc:
            return False

        if scheme == "mailto" and not parsed_url.path:
            return False

        return True

    @staticmethod
    def _sanitize_rich_text_body(body: str) -> str:
        normalized_body = (body or "").strip()
        if not normalized_body:
            return ""

        sanitizer = EmailService._RichTextSanitizer(EmailService)
        sanitizer.feed(normalized_body)
        sanitizer.close()
        sanitized_body = sanitizer.get_html().strip()

        if not sanitized_body:
            return ""

        if "<" not in normalized_body and ">" not in normalized_body:
            return "<br>".join(escape(normalized_body).splitlines())

        return sanitized_body

    @staticmethod
    def _build_inactive_plan_follow_up_message(
        recipient: str,
        recipient_name: str | None,
        subject: str,
        body: str,
    ) -> EmailMessage:
        """Build the manual outreach email for users without an active plan."""
        recipient = EmailService._normalize_single_recipient(recipient)
        smtp_from_email = EmailService._get_setting("SMTP_FROM_EMAIL")
        smtp_from_name = EmailService._get_setting("SMTP_FROM_NAME", "UBA Questionary")
        support_email = EmailService._normalize_smtp_value(
            EmailService._get_setting("SUPPORT_EMAIL")
        ) or smtp_from_email

        if not smtp_from_email:
            raise RuntimeError(
                "SMTP_FROM_EMAIL must be configured when SMTP is enabled."
            )

        formatted_body = EmailService._sanitize_rich_text_body(body)

        html_body = f"<html><body>{formatted_body}</body></html>"

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = f"{smtp_from_name} <{smtp_from_email}>"
        message["To"] = recipient
        message["Reply-To"] = support_email
        message.set_content(html_body, subtype="html")

        return message

    @staticmethod
    def _send_message(message: EmailMessage, require_enabled: bool = False) -> None:
        """Deliver a prepared email message via SMTP."""
        delivery_settings = EmailService._get_smtp_delivery_settings(
            require_enabled=require_enabled
        )
        if delivery_settings is None:
            return

        smtp = None

        try:
            smtp_class = (
                smtplib.SMTP_SSL
                if delivery_settings["smtp_use_ssl"]
                else smtplib.SMTP
            )
            smtp = smtp_class(
                delivery_settings["smtp_host"],
                delivery_settings["smtp_port"],
                timeout=30,
            )
            smtp.ehlo()

            if (
                delivery_settings["smtp_use_tls"]
                and not delivery_settings["smtp_use_ssl"]
            ):
                smtp.starttls()
                smtp.ehlo()

            if (
                delivery_settings["smtp_username"]
                and delivery_settings["smtp_password"]
            ):
                smtp.login(
                    delivery_settings["smtp_username"],
                    delivery_settings["smtp_password"],
                )

            smtp.send_message(message)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            raise RuntimeError("Unable to send email.") from exc
        finally:
            if smtp is not None:
                try:
                    smtp.quit()
                except smtplib.SMTPServerDisconnected:
                    pass

    @staticmethod
    def send_password_reset_email(recipient: str, reset_token: str) -> None:
        """Send a password reset email when SMTP delivery is enabled."""
        message = EmailService._build_password_reset_message(recipient, reset_token)

        try:
            EmailService._send_message(message)
        except RuntimeError as exc:
            raise RuntimeError("Unable to send password reset email.") from exc

    @staticmethod
    def send_inactive_plan_follow_up_email(
        recipient: str,
        recipient_name: str | None,
        subject: str,
        body: str,
    ) -> None:
        """Send a manual outreach email to a user without an active plan."""
        message = EmailService._build_inactive_plan_follow_up_message(
            recipient=recipient,
            recipient_name=recipient_name,
            subject=subject,
            body=body,
        )
        try:
            EmailService._send_message(message, require_enabled=True)
        except RuntimeError as exc:
            raise RuntimeError("Unable to send inactive-plan follow-up email.") from exc
