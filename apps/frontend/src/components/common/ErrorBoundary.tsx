import { Component, ErrorInfo, PropsWithChildren, ReactNode } from "react";
import { ErrorPanel } from "@/components/common/ErrorPanel";

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<PropsWithChildren, ErrorBoundaryState> {
  public state: ErrorBoundaryState = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("Unhandled UI error", error, info);
  }

  public render(): ReactNode {
    if (this.state.hasError) {
      return <ErrorPanel title="Unexpected UI error" error={this.state.error} />;
    }

    return this.props.children;
  }
}
