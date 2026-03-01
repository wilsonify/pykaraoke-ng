Feature: Library Management
  As a karaoke DJ
  I want to manage my song library folders
  So that the application can scan and index my music collection

  Scenario: Scanning the library updates the status bar
    Given the application is running
    And the backend is connected
    When the user clicks the scan library button
    Then the status bar should indicate scanning activity

  Scenario: Adding a folder path updates the status bar
    Given the application is running
    And the backend is connected
    When the user enters "/app/fixtures" in the folder input
    And the user clicks the add folder button
    Then the status bar should confirm the folder was added or show an error

  Scenario: Adding an empty folder path shows a warning
    Given the application is running
    When the user clears the folder input
    And the user clicks the add folder button
    Then the status bar should display "Enter a folder path first"
