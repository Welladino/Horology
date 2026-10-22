"""What a gateway connection can do, as shown on the shared consent page."""
from policy import authorize

NOTE = ('Google sign-in verifies your identity. It does not grant Gmail or Google Drive access. '
        'Your existing policy limits still apply; reconnecting does not reset quotas.')


def gateway_consent(policy):
    """Return (sections, tool names) for the consent page from the shared access policy."""
    tools = authorize(policy, 'gateway_status')['tools']
    sections = []
    if any(t.startswith("supabase_") for t in tools):
        sections.append(("Database metadata", "Inspect approved schemas and database performance. No row writes or access to Auth."))
    for provider, label, prefix in (("tavily", "Web search", "tavily_"), ("firecrawl", "Page scraping", "firecrawl_")):
        if any(t.startswith(prefix) for t in tools):
            budget = policy["budgets"][provider]
            sections.append((label, f'{provider.title()}: {budget["daily"]} credits daily, {budget["monthly"]} monthly. No per-session call cap.'))
    if "publish_synthesis" in tools:
        sections.append(("Synthesis publishing", "Publish static HTML and images to a Pipeline-specific Cloudflare Pages branch in your configured workspace."))
    return sections, tools
