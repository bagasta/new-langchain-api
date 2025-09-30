import "./Loader.css";

interface LoaderProps {
  message?: string;
}

function Loader({ message }: LoaderProps) {
  return (
    <div className="loader-container">
      <div className="spinner" />
      {message ? <p>{message}</p> : null}
    </div>
  );
}

export default Loader;
