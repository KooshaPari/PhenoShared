require 'yaml'
require 'open3'
require 'minitest/autorun'

class CiGateTest < Minitest::Test
  def parse_workflow(source)
    YAML.safe_load(source, permitted_classes: [], permitted_symbols: [], aliases: false)
  end

  def setup
    @jobs = parse_workflow(File.read(File.expand_path('../.github/workflows/ci.yml', __dir__))).fetch('jobs')
    @job = @jobs.fetch('test')
  end

  def test_workflow_rejects_object_tags
    assert_raises(Psych::DisallowedClass) { parse_workflow('--- !ruby/object:Object {}') }
  end

  def test_workflow_rejects_aliases
    assert_raises(Psych::BadAlias) { parse_workflow("a: &a []\nb: *a\n") }
  end

  def test_node_setup_does_not_require_a_lockfile
    node = @jobs.fetch('typescript').fetch('steps').find { |s| s.fetch('uses', '').start_with?('actions/setup-node@') }
    refute node.fetch('with').key?('cache'), 'Unconditional npm cache breaks package.json-only projects'
  end

  def test_regression_is_mandatory_and_precedes_gate
    steps = @job.fetch('steps')
    index = steps.index { |s| s['name'] == 'Verify gate regression controls' }
    refute_nil index
    assert_equal 'ruby tests/test_ci_gate.rb', steps.fetch(index).fetch('run')
    refute steps.fetch(index).key?('if')
    refute steps.fetch(index).fetch('continue-on-error', false)
    refute @job.fetch('continue-on-error', false)
    assert_operator index, :<, steps.index { |s| s['name'] == 'Test gate' }
  end

  %w[rust cargo-deny python go typescript security dep-review].each do |dependency|
    %w[success failure cancelled skipped unknown].each do |result|
      define_method("test_aggregate_#{dependency}_#{result}") do
        step = @jobs.fetch('lint').fetch('steps').find { |s| s['name'] == 'Aggregate lint gate' }
        script = step.fetch('run').gsub(/\$\{\{ needs\.([\w-]+)\.result \}\}/) do
          Regexp.last_match(1) == dependency ? result : 'success'
        end
        output, status = Open3.capture2e('bash', '-e', '-o', 'pipefail', '-c', script)
        assert_equal(%w[success skipped].include?(result), status.success?, output)
      end
    end
  end

  def test_gate_runs_even_when_dependency_fails
    assert_equal 'always()', @job.fetch('if')
    assert_equal ['lint'], @job.fetch('needs')
  end

  def test_pinned_runtime_and_credential_free_checkout
    steps = @job.fetch('steps')
    checkout = steps.find { |s| s.fetch('uses', '').start_with?('actions/checkout@') }
    assert_match(/@[0-9a-f]{40}\z/, checkout.fetch('uses'))
    assert_equal false, checkout.fetch('with', {})['persist-credentials']
    runtime = steps.find { |s| s.fetch('uses', '').start_with?('ruby/setup-ruby@') }
    assert_match(/@[0-9a-f]{40}\z/, runtime.fetch('uses'))
    assert_equal '3.3.6', runtime.fetch('with').fetch('ruby-version')
    install = steps.find { |s| s['name'] == 'Install gate test dependency' }
    assert_equal 'gem install minitest --version 5.25.5 --no-document', install.fetch('run')
  end

  %w[success failure cancelled skipped unknown].each do |result|
    define_method("test_detection_#{result}_with_skipped_language_jobs") do
      step = @jobs.fetch('lint').fetch('steps').find { |s| s['name'] == 'Aggregate lint gate' }
      script = step.fetch('run').gsub(/\$\{\{ needs\.([\w-]+)\.result \}\}/) do
        Regexp.last_match(1) == 'detect' ? result : 'skipped'
      end
      output, status = Open3.capture2e('bash', '-e', '-o', 'pipefail', '-c', script)
      assert_equal(result == 'success', status.success?, output)
    end
  end

  %w[success failure cancelled skipped unknown].each do |result|
    define_method("test_lint_#{result}") do
      step = @job.fetch('steps').find { |s| s['name'] == 'Test gate' }
      env = step.fetch('env', {}).transform_values do |value|
        value.gsub('${{ needs.lint.result }}', result)
      end
      output, status = Open3.capture2e(env, 'bash', '--noprofile', '--norc',
                                      '-e', '-o', 'pipefail', '-c', step.fetch('run'))
      assert_equal(result == 'success', status.success?, output)
    end
  end
end
