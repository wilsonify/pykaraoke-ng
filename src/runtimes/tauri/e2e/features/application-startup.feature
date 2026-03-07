Feature: Application Startup
  As a karaoke user
  I want the application to launch reliably
  So that I can begin browsing and playing songs

  Scenario: User launches the application successfully
    Given the application is not running
    When the user launches the application
    Then the main window should be visible
    And the primary action button should be enabled

  Scenario: Application connects to the backend on startup
    Given the application is not running
    When the user launches the application
    Then the backend status should show "Connected"
    And the status bar should display "Backend connected"

  Scenario: Application renders without JavaScript errors
    Given the application is running
    Then the app container should be present in the DOM
    And no JavaScript crash should have occurred
