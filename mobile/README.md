# Muslim LLM for iOS

The iOS app is a Capacitor 8 shell for the production Muslim LLM web application.

- Bundle identifier: `com.muslimllm.app`
- Team: `A532UHKDZC`
- Deployment target: iOS 15
- Production origin: `https://muslim-llm.148.113.203.232.sslip.io`
- Project: `mobile/ios/App/App.xcodeproj`

## Local validation

```bash
cd mobile
npm ci
npx cap sync ios
cd ..
xcodebuild -project mobile/ios/App/App.xcodeproj \
  -scheme App \
  -sdk iphonesimulator \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  CODE_SIGNING_ALLOWED=NO build
```

## Release

Run `mobile/scripts/release-ios.sh` on a Mac signed into the Stemata Apple Developer team. The script archives and exports an App Store-signed IPA. Upload uses `mobile/ios/UploadOptions.plist` and Xcode's authenticated App Store Connect session.

GitHub Actions uses the protected `testflight` environment. It requires the App Store Connect API key and distribution certificate secrets named in the workflow. Secret values must never be committed.
