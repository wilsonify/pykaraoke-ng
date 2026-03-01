Feature: Error State Handling
  As a karaoke user
  I want the application to handle errors gracefully
  So that the app remains usable even when things go wrong

  Scenario: Application handles backend disconnection gracefully
    Given the application is running
    When the backend becomes unreachable
    Then the status bar should indicate the backend is unreachable
    And the app should remain stable

  Scenario: Clicking buttons when backend is disconnected does not crash
    Given the application is running
    And the backend is not connected
    When the user clicks the play button
    Then the app should remain stable

  Scenario: Search with no backend shows appropriate status
    Given the application is running
    And the backend is not connected
    When the user searches for "test"
    Then the status bar should indicate a search failure or no connection
