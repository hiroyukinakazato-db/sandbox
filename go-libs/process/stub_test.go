package process_test

import (
	"context"
	"fmt"
	"os/exec"
	"testing"

	"github.com/databrickslabs/sandbox/go-libs/env"
	"github.com/databrickslabs/sandbox/go-libs/process"
	"github.com/stretchr/testify/require"
)

func TestStubOutput(t *testing.T) {
	ctx := context.Background()
	ctx, stub := process.WithStub(ctx)
	stub.WithStdout("meeee")

	ctx = env.Set(ctx, "FOO", "bar")

	out, err := process.Background(ctx, []string{"/usr/local/bin/meeecho", "1", "--foo", "bar"})
	require.NoError(t, err)
	require.Equal(t, "meeee", out)
	require.Equal(t, 1, stub.Len())
	require.Equal(t, []string{"meeecho 1 --foo bar"}, stub.Commands())

	allEnv := stub.CombinedEnvironment()
	require.Equal(t, "bar", allEnv["FOO"])
	require.Equal(t, "bar", stub.LookupEnv("FOO"))
}

func TestStubFailure(t *testing.T) {
	ctx := context.Background()
	ctx, stub := process.WithStub(ctx)
	stub.WithFailure(fmt.Errorf("nope"))

	_, err := process.Background(ctx, []string{"/bin/meeecho", "1"})
	require.EqualError(t, err, "/bin/meeecho 1: nope")
	require.Equal(t, 1, stub.Len())
}

func TestStubCallback(t *testing.T) {
	ctx := context.Background()
	ctx, stub := process.WithStub(ctx)
	stub.WithCallback(func(cmd *exec.Cmd) error {
		cmd.Stderr.Write([]byte("something..."))
		cmd.Stdout.Write([]byte("else..."))
		return fmt.Errorf("yep")
	})

	_, err := process.Background(ctx, []string{"/bin/meeecho", "1"})
	require.EqualError(t, err, "/bin/meeecho 1: yep")
	require.Equal(t, 1, stub.Len())

	var processError *process.ProcessError
	require.ErrorAs(t, err, &processError)
	require.Equal(t, "something...", processError.Stderr)
	require.Equal(t, "else...", processError.Stdout)
}

func TestStubResponses(t *testing.T) {
	ctx := context.Background()
	ctx, stub := process.WithStub(ctx)
	stub.
		WithStdoutFor("qux 1", "first").
		WithStdoutFor("qux 2", "second").
		WithFailureFor("qux 3", fmt.Errorf("nope"))

	first, err := process.Background(ctx, []string{"/path/is/irrelevant/qux", "1"})
	require.NoError(t, err)
	require.Equal(t, "first", first)

	second, err := process.Background(ctx, []string{"/path/is/irrelevant/qux", "2"})
	require.NoError(t, err)
	require.Equal(t, "second", second)

	_, err = process.Background(ctx, []string{"/path/is/irrelevant/qux", "3"})
	require.EqualError(t, err, "/path/is/irrelevant/qux 3: nope")

	require.Equal(t, "process stub with 3 calls", stub.String())
}
