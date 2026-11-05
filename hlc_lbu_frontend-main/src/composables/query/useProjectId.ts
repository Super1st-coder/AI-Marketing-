export default function useProjectId() {
  const route = useRoute();
  const projectId = parseInt(route.params.projectId as string);

  return projectId;
}
