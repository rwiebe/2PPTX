# Container security review — 2026-10-19

Head introducing the scan and process isolation: 79619d1.
First PR scan: https://github.com/rwiebe/2PPTX/actions/runs/39294393122

## Current runtime cleanup

The Dockerfile now uses Wolfi with Python 3.12, libstdc++ and tzdata. The
application dependencies are installed in a separate build stage, and only
the virtual environment and application assets are copied into the final stage.
The service runs as app with root-owned application files.

The initial Wolfi scan found zero OS CVEs, but detected a vendored setuptools
component in pip. The final stage therefore uninstalls pip and removes
ensurepip and its bootstrap wheels. This removes actual installer code, not
scanner metadata. The APK package database is retained. The py3-pip-wheel package
record remains in the OS inventory although its optional bootstrap files are
pruned from the service image; installing packages at runtime is unsupported.

CI checks that the former unnecessary Debian tools and Python installation
tools are absent, Python remains 3.12, and real conversion still succeeds.
The full CVE scan includes all severities and unfixed CVEs. HIGH/CRITICAL findings
remain blocking without ignore rules or waivers. A successful run at the current
head is required before release.

## Historical Debian scan outcome

The full Trivy scan ran successfully, but the HIGH/CRITICAL policy gate failed.
It reports 44 HIGH package findings representing eight distinct CVEs in Debian
13.7 source packages. No HIGH/CRITICAL Python package findings were reported.
There are no ignore rules, suppressed unfixed findings, or risk waivers.

The scan is an inventory check, not proof that every finding is remotely
exploitable. The following reachability assessment is based on the application
and default Compose configuration. It does not change the blocking policy.
The Debian Security Tracker currently lists no fixed stable versions for these
eight CVEs. Switching to Bookworm would not resolve them either.

| CVE | Source package | Relevant behavior | Assessment in default deployment |
| --- | --- | --- | --- |
| CVE-2026-76642 | util-linux | Privileged mount helper post-hooks | The application invokes Python conversion only; it does not invoke mount helpers. Runs as app with no-new-privileges. |
| CVE-2026-78408 | util-linux | Root nsenter --join-cgroup descriptor inheritance | No nsenter invocation or root namespace-management workflow in the application. Host operators must still avoid vulnerable host tools. |
| CVE-2026-78409 | util-linux | fstab-authorized X-mount.subdir symlink traversal | No application-managed mounts or fstab entries. |
| CVE-2026-78410 | util-linux | SUID restricted bind mount ownership changes | No application-managed bind mounts or ownership-changing mount hooks; no-new-privileges blocks gaining privilege through SUID. |
| CVE-2026-54369 | acl | Privileged pathname-based ACL manipulation | Application does not manipulate ACLs or run a privileged ACL caller. |
| CVE-2025-69720 | ncurses | Buffer overflow in infocmp command-line tool | No infocmp invocation or terminal-information uploads. PDF/image parsers do not use this CLI path. |
| CVE-2026-16742 | systemd | systemd-homed group escalation | Gunicorn, not systemd, is the container service. No homed-managed login workflow. |
| CVE-2026-9538 | perl | Archive::Tar unbounded tar entry allocation | Application accepts PDF/images; it does not invoke Perl Archive::Tar. |

Authoritative status and descriptions:
- https://security-tracker.debian.org/tracker/CVE-2026-76642
- https://security-tracker.debian.org/tracker/CVE-2026-78408
- https://security-tracker.debian.org/tracker/CVE-2026-78409
- https://security-tracker.debian.org/tracker/CVE-2026-78410
- https://security-tracker.debian.org/tracker/CVE-2026-54369
- https://security-tracker.debian.org/tracker/CVE-2025-69720
- https://security-tracker.debian.org/tracker/CVE-2026-16742
- https://security-tracker.debian.org/tracker/CVE-2026-9538

## Implemented resource isolation

Native conversion runs in a fresh subprocess. Linux enforces a 320-MiB address
space limit, 60-second CPU limit, 64-MiB per-file limit, and disabled core dumps
before the parsers are imported. The parent kills and waits for a process after
90 seconds, returns a controlled error on timeout/crash/resource exhaustion,
and cleans the temporary inputs/output. One conversion per web process remains
the default. The outer 512-MiB container limit is still enforced.

These are resource limits, not a security sandbox for arbitrary native-code
execution. The converter retains the container's unprivileged identity and
filesystem/network permissions. Proxy access and rate limits remain necessary.

## Historical Debian release decision

The Debian-based image was blocked under the strict gate. The smaller Wolfi
runtime above replaces that image; the historical Debian package findings are
not ignored or waived in the scanner. Do not describe any image as inherently
vulnerability-free: the current image must pass the live scan. The workflow runs functional/container tests
before applying the blocking CVE gate so a scan finding does not hide test results.
