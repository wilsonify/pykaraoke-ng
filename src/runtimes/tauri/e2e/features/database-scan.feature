Feature: Database Scan and Report
  As an administrator
  I want to scan a song directory and generate a report
  So that I can verify the library indexing works end-to-end

  @requires-python @requires-selenium
  Scenario: Scanning a directory produces an HTML report listing found songs
    Given a temporary songs directory with a file "SampleArtist-SampleTitle.kar"
    When the database scan runs against the songs directory
    Then an HTML report should be generated
    And the report title should be "PyKaraoke Scan Report"
    And the report should list "SampleArtist-SampleTitle.kar"
