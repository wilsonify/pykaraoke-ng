Feature: Tauri Packaging Integrity
  As a developer
  I want to verify that the Tauri build configuration is correct
  So that the packaged application works reliably on all platforms

  Scenario: WebKitGTK DMA-BUF workaround is present in main.rs
    Given the Tauri source files are available
    Then main.rs should set WEBKIT_DISABLE_DMABUF_RENDERER
    And the workaround should be Linux-only
    And the workaround should respect existing environment values
    And the workaround should be applied before the Tauri builder starts

  Scenario: Backend script path resolution supports multiple layouts
    Given the Tauri source files are available
    Then main.rs should try at least 2 candidate paths for backend.py
    And main.rs should check path existence before use
    And main.rs should use resource_dir for bundled installs

  Scenario: Tauri bundle includes Python backend resources
    Given the Tauri configuration file is available
    Then the bundle should declare resources
    And backend.py should be reachable via bundled resources
    And the beforeBuildCommand should stage the backend

  Scenario: JavaScript does not crash when Tauri API is unavailable
    Given the frontend source files are available
    Then app.js should not destructure window.__TAURI__ at top level
    And app.js should wrap Tauri API access in try-catch
    And app.js should provide a fallback invoke function
