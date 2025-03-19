ls #bash

export TARGET_NAME="kensclaude"
docker container ls 
sleep 1
docker container ls |grep $TARGET_NAME
sleep 1 
# export KENSCLAUDE_CONTAINER_ID=$(docker container ls | awk 'NR>1 {print $1}')
export KENSCLAUDE_CONTAINER_ID=$(docker container ls | grep $TARGET_NAME | awk '{print $1}')

print $KENSCLAUDE_CONTAINER_ID
sleep 1

docker exec -it $KENSCLAUDE_CONTAINER_ID bash

# # Using awk
# container_ids_awk=$(docker container ls | awk 'NR>1 {print $1}')
# echo "Container IDs (awk): $container_ids_awk"

# # Using cut
# container_ids_cut=$(docker container ls | tail -n +2 | cut -d' ' -f1)
# echo "Container IDs (cut): $container_ids_cut"

