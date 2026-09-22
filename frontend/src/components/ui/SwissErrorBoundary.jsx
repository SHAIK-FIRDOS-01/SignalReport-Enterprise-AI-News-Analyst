import React from 'react';

/**
 * Isolated Swiss Error Boundary & Crash Barrier.
 *
 * Traps unhandled JavaScript rendering exceptions within bounded component subtrees,
 * isolating catastrophic crashes from cascading to the root DOM tree and avoiding white screens.
 * Implements stark Swiss brutalist fallback ergonomics and state reinitialization.
 */
export class SwissErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({ errorInfo });
    if (typeof this.props.onError === 'function') {
      this.props.onError(error, errorInfo);
    }
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
    if (typeof this.props.onReset === 'function') {
      this.props.onReset();
    }
  };

  render() {
    const { hasError, error } = this.state;
    const { children, fallback, moduleName = 'CORE_SUBSYSTEM' } = this.props;

    if (hasError) {
      if (fallback) {
        return typeof fallback === 'function' ? fallback({ error, reset: this.handleReset }) : fallback;
      }

      return (
        <div
          data-testid="swiss-error-boundary-fallback"
          className="w-full my-4 border-2 border-swiss-black bg-swiss-white p-6 sm:p-8 shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] relative"
          role="alert"
        >
          {/* Top brutalist status rail */}
          <div className="flex flex-wrap items-center justify-between gap-2 border-b-2 border-swiss-black pb-3 mb-4 font-mono text-xs font-bold">
            <span className="text-swiss-red flex items-center gap-1.5 uppercase tracking-wider">
              <span className="inline-block w-2 h-2 bg-swiss-red"></span>
              [ISOLATED FAULT BARRIER // {moduleName.toUpperCase()}]
            </span>
            <span className="text-swiss-black/60 uppercase">
              STATUS // RENDER_CRASH_TRAPPED
            </span>
          </div>

          {/* Headline */}
          <h2 className="text-lg sm:text-xl font-black uppercase tracking-tight text-swiss-black mb-2">
            An Unexpected Rendering Exception Occurred
          </h2>

          <p className="text-xs sm:text-sm text-swiss-black/80 font-sans mb-4 max-w-2xl leading-relaxed">
            The isolated execution barrier trapped a critical component failure. The surrounding application
            runtime remains active and secure. You may attempt to re-initialize this subsystem.
          </p>

          {/* Monospaced error telemetry dump */}
          <div className="border border-swiss-black/30 bg-neutral-100 p-3 mb-6 font-mono text-xs text-swiss-black break-all overflow-x-auto">
            <div className="font-bold text-swiss-red mb-1">[ERROR TRACE]</div>
            <div>{error?.message || 'Unknown runtime anomaly encountered'}</div>
          </div>

          {/* Swiss stark reset action */}
          <button
            type="button"
            data-testid="error-boundary-reset"
            onClick={this.handleReset}
            className="inline-flex items-center justify-center bg-swiss-black text-swiss-white font-mono uppercase tracking-widest px-5 py-2.5 text-xs font-bold hover:bg-swiss-red transition-colors border-2 border-swiss-black cursor-pointer shadow-[2px_2px_0px_0px_rgba(0,0,0,0.5)] active:translate-x-0.5 active:translate-y-0.5"
          >
            RECOVER ENGINE // RE-INITIALIZE
          </button>
        </div>
      );
    }

    return children;
  }
}

export default SwissErrorBoundary;
