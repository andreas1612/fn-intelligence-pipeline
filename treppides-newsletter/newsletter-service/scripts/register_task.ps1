# Registers a nightly (02:00) Windows Scheduled Task for the newsletter pipeline,
# then leaves it DISABLED. Run from newsletter-service/. Safe to re-run.
# The task still will not do anything until SCHEDULE_ENABLED=true in .env.

$ErrorActionPreference = "Stop"
$root   = (Resolve-Path "$PSScriptRoot\..").Path
$python = Join-Path $root ".venv\Scripts\python.exe"
$name   = "TreppidesNewsletterDaily"

# Run inside the service dir so `-m src.pipeline` resolves.
$action  = New-ScheduledTaskAction -Execute $python -Argument "-m src.pipeline" -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -Daily -At 2:00am
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd

Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger `
  -Settings $settings -Description "Treppides newsletter nightly pipeline" -Force | Out-Null

# Leave it disabled - the mechanism exists but does not fire yet.
Disable-ScheduledTask -TaskName $name | Out-Null

Write-Output "Registered '$name' (DAILY 02:00) and left it DISABLED."
Write-Output "To activate: Enable-ScheduledTask -TaskName $name  AND set SCHEDULE_ENABLED=true in .env"
