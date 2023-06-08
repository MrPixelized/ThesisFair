export const canGetStudentVotes = (req, args) => {
  if (!(req.user.type === 'a' || (req.user.type === 's' && req.user.uid === args.uid))) {
    throw new Error('UNAUTHORIZED get this students votes');
  }
}

export const canGetEntityVotes = (req, args) => {
  if (!(req.user.type === 'a' || (req.user.type === 'r' && req.user.enid === args.enid))) {
    throw new Error('UNAUTHORIZED get this entities votes');
  }
}

export const canVote = (req, args) => {
  if (!(req.user.type === 'a' || (req.user.type === 's' && req.user.uid === args.uid))) {
    throw new Error('UNAUTHORISED cast vote as this user');
  }
}
