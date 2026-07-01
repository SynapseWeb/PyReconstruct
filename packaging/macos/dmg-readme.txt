How to open PyReconstruct (first launch)
========================================

PyReconstruct is not yet code-signed by Apple (this is a preview build), so the
first time you open it macOS will block it with a dialog like:

    "PyReconstruct" Not Opened
    Apple could not verify "PyReconstruct" is free of malware that may harm
    your Mac or compromise your privacy.
                                              [ Move to Trash ]   [ Done ]

This is expected for an unsigned app. Click "Done" -- do NOT click "Move to
Trash" -- then allow it to run one of these two ways:

Option A -- Terminal (most reliable)
  1. Drag PyReconstruct onto the Applications folder (the alias in this window).
  2. Open Terminal (Applications > Utilities > Terminal), paste this line, and
     press Return:

         xattr -dr com.apple.quarantine /Applications/PyReconstruct.app

     (No output means it worked. If it says "Operation not permitted," put
     "sudo " in front and enter your password.)
  3. Open PyReconstruct from Applications or Launchpad as usual.

Option B -- no Terminal
  1. Drag PyReconstruct onto the Applications folder, double-click it, and click
     "Done" on the dialog above.
  2. Open System Settings > Privacy & Security, scroll down to the Security
     section, and click "Open Anyway" next to the PyReconstruct message.
  3. Confirm, then open PyReconstruct again.

You only need to do this once per install.

This step goes away once PyReconstruct is code-signed and notarized.
